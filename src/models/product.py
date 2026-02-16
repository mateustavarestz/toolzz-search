"""Schema para produtos de e-commerce."""
from decimal import Decimal

from pydantic import BaseModel, Field, HttpUrl


class ProductSpecification(BaseModel):
    """Especificacao tecnica de produto."""

    key: str
    value: str


class ProductReview(BaseModel):
    """Resumo de avaliacoes."""

    rating: float = Field(ge=0, le=5)
    total_reviews: int = Field(ge=0)


class Product(BaseModel):
    """Produto individual."""

    name: str
    price: Decimal = Field(gt=0)
    original_price: Decimal | None = None
    discount_percentage: float | None = Field(default=None, ge=0, le=100)
    description: str | None = None
    brand: str | None = None
    category: str | None = None
    available: bool = True
    stock_quantity: int | None = Field(default=None, ge=0)
    images: list[HttpUrl] = Field(default_factory=list)
    specifications: list[ProductSpecification] = Field(default_factory=list)
    reviews: ProductReview | None = None
    url: HttpUrl


class ProductListPage(BaseModel):
    """Listagem de produtos."""

    products: list[Product]
    total_count: int = Field(ge=0)
    page: int = Field(default=1, ge=1)
    has_next_page: bool = False

