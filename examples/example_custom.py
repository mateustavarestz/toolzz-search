"""Exemplo de scraping com schema customizado."""
import asyncio

from pydantic import BaseModel, HttpUrl

from src.core.orchestrator import ScraperOrchestrator


class JobPosting(BaseModel):
    title: str
    company: str
    location: str
    salary: str | None = None
    description: str
    requirements: list[str]
    posted_date: str | None = None
    apply_url: HttpUrl | None = None


class JobListPage(BaseModel):
    jobs: list[JobPosting]
    total_count: int


async def main() -> None:
    scraper = ScraperOrchestrator()
    result = await scraper.scrape(
        url="https://example.com",
        schema=JobListPage,
        wait_until="domcontentloaded",
        full_page=False,
    )

    if result["success"]:
        print(f"Registros extraidos: {result['data'].get('total_count', 0)}")
        print(f"Custo: ${result['metadata']['cost_usd']:.4f}")
    else:
        print(f"Erro: {result.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())

