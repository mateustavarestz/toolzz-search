"""Exemplo de scraping concorrente de multiplas URLs."""
import asyncio

from src.core.orchestrator import ScraperOrchestrator
from src.models.product import ProductListPage


async def scrape_url(scraper: ScraperOrchestrator, url: str):
    return await scraper.scrape(
        url=url,
        schema=ProductListPage,
        wait_until="domcontentloaded",
    )


async def main() -> None:
    scraper = ScraperOrchestrator(with_storage=False)
    urls = [
        "https://example.com",
        "https://www.iana.org/domains/reserved",
    ]
    results = await asyncio.gather(*(scrape_url(scraper, url) for url in urls), return_exceptions=True)

    for idx, result in enumerate(results, start=1):
        if isinstance(result, Exception):
            print(f"[{idx}] Erro: {result}")
            continue
        print(f"[{idx}] Success: {result['success']}")


if __name__ == "__main__":
    asyncio.run(main())

