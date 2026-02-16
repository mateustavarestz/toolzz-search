"""Schemas para noticias e artigos."""
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class ArticleImage(BaseModel):
    """Imagem associada a artigo."""

    url: HttpUrl
    caption: str | None = None


class Article(BaseModel):
    """Modelo de artigo/noticia."""

    title: str
    subtitle: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    content: str
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    images: list[ArticleImage] = Field(default_factory=list)
    related_links: list[HttpUrl] = Field(default_factory=list)
    url: HttpUrl

