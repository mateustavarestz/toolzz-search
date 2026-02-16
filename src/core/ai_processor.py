"""AI processor para extracao estruturada."""
import asyncio
import json
from typing import Any

from loguru import logger
from openai import OpenAI
from openai import OpenAIError
from pydantic import BaseModel

from src.config.prompts import SYSTEM_PROMPT_GENERIC
from src.config.prompts import AGENT_EXTRACTOR_PROMPT, AGENT_PLANNER_PROMPT
from src.config.settings import settings
from src.core.errors import ModelScraperError
from src.models.agent import AgentAction, AgentState
from src.utils.cost_tracker import calculate_cost
from src.utils.helpers import clean_html


class AIProcessor:
    """Processa screenshot + HTML com GPT-5 mini."""

    def __init__(self, api_key: str | None = None) -> None:
        self.client = OpenAI(api_key=api_key or settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    async def extract_structured_data(
        self,
        screenshot_base64: str,
        html: str,
        text_content: str,
        schema: type[BaseModel],
        system_prompt: str | None = None,
        extraction_goal: str | None = None,
        max_html_chars: int = 50_000,
    ) -> dict[str, Any]:
        """Extrai dados seguindo schema Pydantic informado."""
        html_truncated = clean_html(html, max_chars=max_html_chars)
        text_cut = text_content[:20_000]
        prompt = system_prompt or SYSTEM_PROMPT_GENERIC

        goal_instruction = (
            f"Objetivo do usuario (prioritario): {extraction_goal.strip()}\n\n"
            if extraction_goal and extraction_goal.strip()
            else ""
        )

        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{screenshot_base64}",
                            "detail": "high",
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extraia os dados desta pagina e responda APENAS com JSON valido.\n\n"
                            f"{goal_instruction}"
                            f"Schema esperado:\n{schema.model_json_schema()}\n\n"
                            f"HTML:\n{html_truncated}\n\n"
                            f"Texto renderizado:\n{text_cut}"
                        ),
                    },
                ],
            },
        ]

        logger.info("Chamando OpenAI para extracao estruturada...")
        response = await self._run_chat_completion(messages=messages)
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
            repair_response = await self._run_chat_completion(messages=repair_messages)
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
                "model": self.model,
                "tokens_used": tokens,
                "cost_usd": cost_usd,
            },
        }

    async def plan_next_action(self, state: AgentState, goal: str) -> AgentAction:
        """Planeja proxima acao para loop Selenium."""
        user_text = (
            f"Objetivo: {goal}\n"
            f"Step: {state.step_index}\n"
            f"URL atual: {state.current_url}\n"
            f"Titulo: {state.title or ''}\n"
            f"Texto visivel:\n{state.text_excerpt[:2000]}\n"
            f"Ultimo erro: {state.last_error or 'none'}\n"
        )
        messages = [
            {"role": "system", "content": AGENT_PLANNER_PROMPT},
            {"role": "user", "content": user_text},
        ]
        response = await self._run_chat_completion(messages=messages)
        content = response.choices[0].message.content or "{}"
        try:
            parsed = json.loads(content)
            return AgentAction(**parsed)
        except Exception as exc:  # noqa: BLE001
            raise ModelScraperError(f"Planner retornou acao invalida: {content}") from exc

    async def extract_from_evidence(
        self,
        evidence: list[dict[str, Any]],
        schema: type[BaseModel],
        goal: str,
    ) -> dict[str, Any]:
        """Extrai dados finais a partir de multiplos estados coletados."""
        compact = []
        for item in evidence[-12:]:
            compact.append(
                {
                    "url": item.get("current_url"),
                    "title": item.get("title"),
                    "text_excerpt": (item.get("text_excerpt") or "")[:1800],
                    "last_error": item.get("last_error"),
                }
            )
        messages = [
            {"role": "system", "content": AGENT_EXTRACTOR_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Objetivo:\n{goal}\n\n"
                    f"Schema:\n{schema.model_json_schema()}\n\n"
                    f"Evidencias:\n{json.dumps(compact, ensure_ascii=False)}"
                ),
            },
        ]
        response = await self._run_chat_completion(messages=messages)
        content = response.choices[0].message.content or "{}"
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ModelScraperError("Extractor do agente retornou JSON invalido") from exc
        usage = response.usage
        tokens = {
            "input": usage.prompt_tokens if usage else 0,
            "output": usage.completion_tokens if usage else 0,
            "total": usage.total_tokens if usage else 0,
        }
        return {
            "data": data,
            "metadata": {
                "model": self.model,
                "tokens_used": tokens,
                "cost_usd": calculate_cost(tokens["input"], tokens["output"]),
            },
        }

    async def _run_chat_completion(self, messages: list[dict[str, Any]]) -> Any:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_completion_tokens=5000,
                ),
                timeout=75,
            )
        except asyncio.TimeoutError as exc:
            raise ModelScraperError("Timeout ao chamar API do modelo") from exc
        except OpenAIError as exc:
            raise ModelScraperError(f"Erro da API do modelo: {exc}") from exc

