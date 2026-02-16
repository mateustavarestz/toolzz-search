from pydantic import BaseModel, HttpUrl

from src.core.validator import DataValidator


class DemoSchema(BaseModel):
    name: str
    url: HttpUrl


def test_validate_success():
    data, errors = DataValidator.validate(
        data={"name": "Produto", "url": "https://example.com"},
        schema=DemoSchema,
    )
    assert errors == []
    assert data is not None
    assert data["name"] == "Produto"


def test_validate_error():
    data, errors = DataValidator.validate(
        data={"name": "Produto", "url": "nao-e-url"},
        schema=DemoSchema,
    )
    assert data is None
    assert len(errors) > 0

