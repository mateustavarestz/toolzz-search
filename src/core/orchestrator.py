"""Orquestrador do fluxo completo de scraping."""
import asyncio
import time
from typing import Any

from loguru import logger
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential, wait_random

from src.config.settings import settings
from src.core.ai_processor import AIProcessor
from src.core.browser import BrowserManager
from src.core.errors import (
    BlockedScraperError,
    RecoverableScraperError,
    classify_exception,
    host_from_url,
)
from src.core.storage import StorageManager
from src.core.validator import DataValidator
from src.utils.logger import configure_logging


class ScraperOrchestrator:
    """Executa pipeline completo: browser -> IA -> validacao -> storage."""

    def __init__(self, with_storage: bool = True, api_key: str | None = None) -> None:
        configure_logging()
        self.ai_processor = AIProcessor(api_key=api_key)
        self.validator = DataValidator()
        self.storage = StorageManager() if with_storage else None
        self._domain_locks: dict[str, asyncio.Semaphore] = {}
        self._domain_failure_count: dict[str, int] = {}

    async def scrape(
        self,
        url: str,
        schema: type[BaseModel],
        system_prompt: str | None = None,
        extraction_goal: str | None = None,
        output_format: str = "list",
        extra_metadata: dict[str, Any] | None = None,
        **browser_options: Any,
    ) -> dict[str, Any]:
        """Executa scraping completo em uma URL e persiste a tentativa."""
        if self.storage:
            await self.storage.initialize()

        try:
            result = await self._scrape_with_retry(
                url=url,
                schema=schema,
                system_prompt=system_prompt,
                extraction_goal=extraction_goal,
                output_format=output_format,
                **browser_options,
            )
            # Merge extra_metadata into result metadata if success
            if extra_metadata and "metadata" in result:
                result["metadata"].update(extra_metadata)

        except Exception as exc:
            error_type, retryable = classify_exception(exc)
            logger.exception(f"Falha final no scraping ({error_type}): {exc}")
            result = {
                "success": False,
                "error": str(exc),
                "metadata": {
                    "url": url,
                    "duration_seconds": 0,
                    "extraction_goal": extraction_goal,
                    "error_type": error_type,
                    "retryable": retryable,
                },
            }
            if extra_metadata:
                result["metadata"].update(extra_metadata)

        record_id: int | None = None
        if self.storage:
            record_id = await self.storage.save_attempt(
                payload=result,
                url=url,
                cost_usd=float(result.get("metadata", {}).get("cost_usd", 0) or 0),
            )

        result["record_id"] = record_id
        return result

    @retry(
        stop=stop_after_attempt(settings.RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=settings.RETRY_DELAY, min=1, max=16) + wait_random(0, 1.5),
        retry=retry_if_exception_type((RecoverableScraperError,)),
        reraise=True,
    )
    async def _scrape_with_retry(
        self,
        url: str,
        schema: type[BaseModel],
        system_prompt: str | None = None,
        extraction_goal: str | None = None,
        output_format: str = "list",
        **browser_options: Any,
    ) -> dict[str, Any]:
        start = time.perf_counter()
        logger.info(f"Iniciando scraping: {url}")
        domain = host_from_url(url)
        domain_limit = max(1, min(settings.MAX_CONCURRENT_TASKS, 3))
        lock = self._domain_locks.setdefault(domain, asyncio.Semaphore(domain_limit))
        failure_count = self._domain_failure_count.get(domain, 0)
        if failure_count >= 4:
            raise BlockedScraperError(
                f"Circuit breaker ativo para dominio {domain} (falhas consecutivas={failure_count})"
            )

        async with lock:
            async with BrowserManager() as browser:
                screenshot_b64, html, text_content, ax_snapshot, image_urls, page_metadata = await browser.navigate_and_capture(
                    url=url,
                    **browser_options,
                )

            ai_result = await self.ai_processor.extract_structured_data(
                screenshot_base64=screenshot_b64,
                html=html,
                text_content=text_content,
                accessibility_snapshot=ax_snapshot,
                image_urls=image_urls,
                schema=schema,
                system_prompt=system_prompt,
                extraction_goal=extraction_goal,
                output_format=output_format,
            )
        duration = time.perf_counter() - start

        validated_data, errors, quality = self.validator.validate(ai_result["data"], schema=schema)
        if errors or validated_data is None:
            logger.error(f"Falha na validacao: {errors}")
            return {
                "success": False,
                "error": "Validation failed",
                "validation_errors": errors,
                "metadata": {
                    "url": url,
                    "model_used": ai_result["metadata"]["model"],
                    "tokens_used": ai_result["metadata"]["tokens_used"],
                    "cost_usd": ai_result["metadata"]["cost_usd"],
                    "duration_seconds": duration,
                    "page": page_metadata,
                    "extraction_goal": extraction_goal,
                    "error_type": "validation",
                    "retryable": False,
                    "quality": quality,
                },
            }

        result_metadata = {
            "url": url,
            "model_used": ai_result["metadata"]["model"],
            "tokens_used": ai_result["metadata"]["tokens_used"],
            "cost_usd": ai_result["metadata"]["cost_usd"],
            "duration_seconds": duration,
            "page": page_metadata,
            "extraction_goal": extraction_goal,
            "error_type": None,
            "retryable": False,
            "quality": quality,
        }
        self._domain_failure_count[domain] = 0
        return {"success": True, "data": validated_data, "metadata": result_metadata}

