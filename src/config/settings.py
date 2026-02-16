"""Configurações do sistema carregadas do .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings globais do scraper."""

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5-mini-2025-08-07"

    # Playwright
    HEADLESS: bool = True
    BROWSER_TIMEOUT: int = 30000
    VIEWPORT_WIDTH: int = 1920
    VIEWPORT_HEIGHT: int = 1080

    # Scraping
    MAX_CONCURRENT_TASKS: int = 3
    RETRY_ATTEMPTS: int = 3
    RETRY_DELAY: int = 2

    # Storage
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/scraper_data.db"
    SAVE_SCREENSHOTS: bool = True
    SCREENSHOT_DIR: str = "./data/screenshots"
    EXPORTS_DIR: str = "./data/exports"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/scraper.log"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

