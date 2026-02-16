"""Custom exceptions e helpers de classificacao de erro."""
from urllib.parse import urlparse

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError


class ScraperError(Exception):
    """Erro base do scraper."""


class RecoverableScraperError(ScraperError):
    """Erro temporario que pode ser retentado."""


class NonRecoverableScraperError(ScraperError):
    """Erro deterministico que nao deve ser retentado."""


class BlockedScraperError(RecoverableScraperError):
    """Sinal de bloqueio anti-bot/captcha/challenge."""


class ValidationScraperError(NonRecoverableScraperError):
    """Dados extraidos nao bateram com o schema esperado."""


class ModelScraperError(RecoverableScraperError):
    """Falha em chamada de modelo/fornecedor LLM."""


class NetworkScraperError(RecoverableScraperError):
    """Falha de rede/navegacao."""


def classify_exception(error: Exception) -> tuple[str, bool]:
    """Retorna (error_type, retryable)."""
    if isinstance(error, ValidationScraperError):
        return "validation", False
    if isinstance(error, BlockedScraperError):
        return "blocked", True
    if isinstance(error, ModelScraperError):
        return "model", True
    if isinstance(error, NetworkScraperError):
        return "network", True
    if isinstance(error, PlaywrightTimeoutError):
        return "network", True
    if isinstance(error, PlaywrightError):
        return "network", True
    return "unknown", False


def host_from_url(url: str) -> str:
    """Extrai host de URL para rate limit por dominio."""
    try:
        return urlparse(url).netloc.lower().strip() or "unknown"
    except Exception:
        return "unknown"

