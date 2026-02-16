"""Modelos base do scraping."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class ScrapedData(BaseModel):
    """Modelo base para respostas de scraping."""

    url: HttpUrl
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str | None = None


class ScrapingMetadata(BaseModel):
    """Metadados sobre uma execucao de scraping."""

    url: str
    timestamp: datetime
    model_used: str
    tokens_used: dict[str, Any]
    cost_usd: float
    duration_seconds: float

