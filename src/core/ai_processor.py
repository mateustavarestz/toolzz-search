"""AI processor para extracao estruturada."""
import asyncio
import json
from typing import Any

from loguru import logger
from openai import OpenAI
from openai import AuthenticationError as OpenAIAuthenticationError
from openai import OpenAIError
from pydantic import BaseModel

from src.config.prompts import SYSTEM_PROMPT_GENERIC
from src.config.settings import settings
from src.core.errors import ModelAuthScraperError, ModelScraperError
from src.utils.cost_tracker import calculate_cost
from src.utils.helpers import clean_html


class AIProcessor:
    """Processa screenshot + HTML com GPT-5 mini."""

    def __init__(self, api_key: str | None = None) -> None:
        self.default_api_key = (api_key or settings.OPENAI_API_KEY or "").strip()
        self.default_model = settings.OPENAI_MODEL
        self.client = OpenAI(api_key=self.default_api_key) if self.default_api_key else None

    async def extract_structured_data(
        self,
        screenshot_base64: str,
        html: str,
        text_content: str,
        schema: type[BaseModel],
        accessibility_snapshot: str = "",
        image_urls: list[str] | None = None,
        system_prompt: str | None = None,
        extraction_goal: str | None = None,
        output_format: str = "list",
        openai_api_key: str | None = None,
        openai_model: str | None = None,
        max_html_chars: int = 50_000,
    ) -> dict[str, Any]:
        """Extrai dados seguindo schema Pydantic informado."""
        resolved_api_key = (openai_api_key or self.default_api_key or "").strip()
        api_key_source = "request" if (openai_api_key and openai_api_key.strip()) else "env"
        if not resolved_api_key:
            raise ModelAuthScraperError(
                "OpenAI API key nao configurada. Informe em .env ou no campo de configuracao da interface."
            )
        resolved_model = (openai_model or self.default_model).strip() or self.default_model
        client = self.client if (not openai_api_key and self.client) else OpenAI(api_key=resolved_api_key)
        html_truncated = clean_html(html, max_chars=max_html_chars)
        text_cut = text_content[:20_000]
        prompt = system_prompt or SYSTEM_PROMPT_GENERIC
        
        # OPTIMIZATION: Use Accessibility Snapshot if available
        structure_context = (
            f"Accessibility Tree (Preferred):\n{accessibility_snapshot[:60000]}"
            if accessibility_snapshot
            else f"HTML:\n{html_truncated}"
        )
        
        images_context = ""
        if image_urls:
            images_context = f"Imagens Disponiveis:\n{json.dumps(image_urls[:50], indent=2)}"

        if output_format == "summary":
            format_instruction = (
                "FORMATO DE SAIDA: RESUMO EXECUTIVO (CONCISO).\n"
                "- Foco total no campo 'summary'. Escreva um parágrafo denso e direto sobre o conteudo.\n"
                "- Use Markdown para destacar pontos chave (negrito).\n"
                "- Use a lista 'findings' APENAS para topicos cruciais, sem detalhes excessivos.\n"
                "- Ignore detalhes irrelevantes. Seja breve e direto ao ponto."
            )
        elif output_format == "report":
            format_instruction = (
                "FORMATO DE SAIDA: RELATORIO COMPLETO (DETALHADO).\n"
                "- O campo 'summary' deve ser uma introducao abrangente e rica em contexto. USE MARKDOWN.\n"
                "- Use # Titulos, **Negrito**, - Listas no 'summary' para estruturar o texto como um documento.\n"
                "- SE RELEVANTE, inclua imagens no corpo do texto markdown usando: ![alt](url). Escolha as melhores URLs da lista 'Imagens Disponiveis'.\n"
                "- A lista 'findings' deve ser EXTENSA. Extraia TUDO que for relevante.\n"
                "- As descricoes devem ser longas, detalhadas e analiticas.\n"
                "- Nao economize texto. O usuario quer uma analise profunda e extensa.\n"
                "- Se houver dados tecnicos, use o campo 'extra' para estruturar."
            )
        else:  # list
            format_instruction = (
                "FORMATO DE SAIDA: LISTA ESTRUTURADA (PADRAO).\n"
                "- Foco principal na lista 'findings'.\n"
                "- Identifique cada item individualmente.\n"
                "- Descricoes devem ser objetivas e diretas.\n"
                "- Mantenha o 'summary' curto, apenas como contexto geral."
            )

        goal_instruction = (
            f"Objetivo do usuario (prioritario): {extraction_goal.strip()}\n\n"
            f"{format_instruction}\n"
            if extraction_goal and extraction_goal.strip()
            else f"{format_instruction}\n"
        )

        user_content = []
        if screenshot_base64:
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{screenshot_base64}",
                    "detail": "high",
                },
            })
        
        user_content.append({
            "type": "text",
            "text": (
                "Extraia os dados desta pagina e responda APENAS com JSON valido.\n\n"
                f"{goal_instruction}"
                f"Schema esperado:\n{schema.model_json_schema()}\n\n"
                f"{structure_context}\n\n"
                f"{images_context}\n\n"
                f"Texto renderizado:\n{text_cut}"
            ),
        })

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_content},
        ]

        logger.info("Chamando OpenAI para extracao estruturada...")
        response = await self._run_chat_completion(messages=messages, client=client, model=resolved_model)
        content = response.choices[0].message.content or "{}"
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Segunda tentativa com autocorrecao do JSON para reduzir falhas deterministicas.
            repair_messages = messages + [
                {
                    "role": "assistant",
                    "content": content,
                },
                {
                    "role": "user",
                    "content": (
                        "Corrija sua resposta para JSON estrito e valido, sem texto extra. "
                        "Mantenha o mesmo schema solicitado."
                    ),
                },
            ]
            repair_response = await self._run_chat_completion(
                messages=repair_messages, client=client, model=resolved_model
            )
            repair_content = repair_response.choices[0].message.content or "{}"
            try:
                data = json.loads(repair_content)
                response = repair_response
            except json.JSONDecodeError as exc:
                raise ModelScraperError("LLM retornou JSON invalido apos tentativa de autocorrecao") from exc

        usage = response.usage
        tokens = {
            "input": usage.prompt_tokens if usage else 0,
            "output": usage.completion_tokens if usage else 0,
            "total": usage.total_tokens if usage else 0,
        }
        cost_usd = calculate_cost(
            input_tokens=tokens["input"],
            output_tokens=tokens["output"],
            cached_input_tokens=0,
        )

        return {
            "data": data,
            "metadata": {
                "model": resolved_model,
                "api_key_source": api_key_source,
                "tokens_used": tokens,
                "cost_usd": cost_usd,
            },
        }



    async def _run_chat_completion(
        self,
        messages: list[dict[str, Any]],
        client: OpenAI,
        model: str,
    ) -> Any:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    client.chat.completions.create,
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                ),
                timeout=75,
            )
        except asyncio.TimeoutError as exc:
            raise ModelScraperError("Timeout ao chamar API do modelo") from exc
        except OpenAIAuthenticationError as exc:
            raise ModelAuthScraperError(
                f"Credencial OpenAI invalida/sem permissao: {exc}"
            ) from exc
        except OpenAIError as exc:
            raise ModelScraperError(f"Erro da API do modelo: {exc}") from exc

