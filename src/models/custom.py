"""Exemplos de schemas customizaveis."""
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class GenericEntity(BaseModel):
    """Entidade generica para extracao livre."""

    title: str
    description: str | None = None
    url: HttpUrl | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class GenericListPage(BaseModel):
    """Lista generica de entidades extraidas."""

    items: list[GenericEntity] = Field(default_factory=list)
    total_count: int = 0


class GuidedExtractionResult(BaseModel):
    """Resultado guiado por prompt livre do usuario."""

    objective: str
    summary: str | None = None
    findings: list[GenericEntity] = Field(default_factory=list)
    total_count: int = 0

