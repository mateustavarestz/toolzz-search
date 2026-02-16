"""Configuracao central de logging."""
from contextvars import ContextVar
from pathlib import Path

from loguru import logger

from src.config.settings import settings

REQUEST_ID_CTX: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(request_id: str) -> None:
    REQUEST_ID_CTX.set(request_id)


def clear_request_id() -> None:
    REQUEST_ID_CTX.set("-")


def configure_logging() -> None:
    """Configura saídas de log para console e arquivo."""
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.configure(
        patcher=lambda record: record["extra"].update({"request_id": REQUEST_ID_CTX.get()}),
    )
    fmt = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | rid={extra[request_id]} | "
        "{name}:{function}:{line} - {message}"
    )
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level=settings.LOG_LEVEL.upper(),
        colorize=False,
        format=fmt,
    )
    logger.add(
        str(log_path),
        level=settings.LOG_LEVEL.upper(),
        rotation="10 MB",
        retention="10 days",
        enqueue=True,
        backtrace=False,
        diagnose=False,
        format=fmt,
    )

