"""API web para o scraper inteligente."""
import time
from uuid import uuid4
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from src.config.prompts import (
    SYSTEM_PROMPT_ECOMMERCE,
    SYSTEM_PROMPT_GENERIC,
    SYSTEM_PROMPT_NEWS,
)
from src.core.orchestrator import ScraperOrchestrator
from src.core.storage import StorageManager
from src.models.article import Article
from src.models.custom import GenericListPage, GuidedExtractionResult
from src.models.product import ProductListPage
from src.utils.logger import clear_request_id, set_request_id

app = FastAPI(
    title="Toolzz Search - AI Scraper",
    version="1.0.0",
    description="Interface web para scraping inteligente com Playwright + GPT-5 mini.",
)

SCHEMA_MAP: dict[str, type[BaseModel]] = {
    "product_list": ProductListPage,
    "article": Article,
    "generic_list": GenericListPage,
    "guided_extract": GuidedExtractionResult,
}

PROMPT_MAP: dict[str, str] = {
    "generic": SYSTEM_PROMPT_GENERIC,
    "ecommerce": SYSTEM_PROMPT_ECOMMERCE,
    "news": SYSTEM_PROMPT_NEWS,
}

SCRAPE_REQUESTS_TOTAL = Counter(
    "scrape_requests_total",
    "Total de requests de scraping",
    ["status", "error_type"],
)
SCRAPE_DURATION_SECONDS = Histogram(
    "scrape_duration_seconds",
    "Duracao das execucoes de scraping",
)
SCRAPE_COST_USD_TOTAL = Counter(
    "scrape_cost_usd_total",
    "Custo total de scraping em USD",
)
SCRAPE_VALIDATION_FAILURES_TOTAL = Counter(
    "scrape_validation_failures_total",
    "Falhas de validacao de schema",
)



class ScrapeRequest(BaseModel):
    """Payload recebido do frontend."""

    model_config = ConfigDict(populate_by_name=True)

    url: str = Field(min_length=5)
    schema_name: str = Field(default="generic_list", alias="schema")
    prompt: str = Field(default="generic")
    user_prompt: str | None = Field(default=None, max_length=4000)
    wait_until: str = Field(default="networkidle")
    timeout: int = Field(default=30_000, ge=5_000, le=120_000)
    full_page: bool = False
    screenshot_quality: int = Field(default=70, ge=30, le=100)
    auto_scroll: bool = True
    scroll_steps: int = Field(default=6, ge=1, le=20)
    output_format: str = Field(default="list", pattern="^(list|summary|report)$")
    openai_api_key: str | None = Field(default=None, max_length=300)
    openai_model: str | None = Field(default=None, max_length=120)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|192\.168\.\d+\.\d+)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next: Any) -> Response:
    request_id = request.headers.get("x-request-id") or str(uuid4())
    set_request_id(request_id)
    try:
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response
    finally:
        clear_request_id()


@app.get("/")
async def home() -> dict[str, str]:
    """Endpoint raiz informativo."""
    return {
        "service": "toolzz-search-api",
        "status": "ok",
        "docs": "/docs",
        "scrape_endpoint": "/api/scrape",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check simples para diagnostico local."""
    return {"status": "ok"}


@app.post("/api/scrape")
async def scrape(payload: ScrapeRequest) -> dict[str, Any]:
    """Executa scraping com parametros enviados pela interface."""
    schema_cls = SCHEMA_MAP.get(payload.schema_name)
    if not schema_cls:
        return {"success": False, "error": f"Schema invalido: {payload.schema_name}"}

    system_prompt = PROMPT_MAP.get(payload.prompt, SYSTEM_PROMPT_GENERIC)

    start = time.perf_counter()
    scraper = ScraperOrchestrator(with_storage=True)
    runtime_api_key = payload.openai_api_key.strip() if payload.openai_api_key else None
    runtime_model = payload.openai_model.strip() if payload.openai_model else None
    result = await scraper.scrape(
        url=payload.url,
        schema=schema_cls,
        system_prompt=system_prompt,
        extraction_goal=payload.user_prompt,
        openai_api_key=runtime_api_key,
        openai_model=runtime_model,
        wait_until=payload.wait_until,
        timeout=payload.timeout,
        full_page=payload.full_page,
        screenshot_quality=payload.screenshot_quality,
        auto_scroll=payload.auto_scroll,
        scroll_steps=payload.scroll_steps,
        output_format=payload.output_format,
    )
    elapsed = time.perf_counter() - start
    SCRAPE_DURATION_SECONDS.observe(elapsed)
    metadata = result.get("metadata", {})
    cost = float(metadata.get("cost_usd", 0) or 0)
    if cost > 0:
        SCRAPE_COST_USD_TOTAL.inc(cost)
    if result.get("success"):
        SCRAPE_REQUESTS_TOTAL.labels(status="success", error_type="none").inc()
    else:
        err = str(metadata.get("error_type", "unknown"))
        SCRAPE_REQUESTS_TOTAL.labels(status="error", error_type=err).inc()
        if err == "validation":
            SCRAPE_VALIDATION_FAILURES_TOTAL.inc()
    return result


@app.get("/api/history")
async def history(limit: int = 20, success: bool | None = None, domain: str | None = None) -> dict[str, Any]:
    """Retorna historico recente salvo no SQLite."""
    storage = StorageManager()
    await storage.initialize()
    items = await storage.list_recent(limit=limit, success=success, domain=domain)
    await storage.close()
    return {"success": True, "count": len(items), "items": items}


@app.get("/metrics")
async def metrics() -> Response:
    """Endpoint Prometheus."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)




