"""Exemplo de scraping de listagem de produtos."""
import asyncio

from src.config.prompts import SYSTEM_PROMPT_ECOMMERCE
from src.core.orchestrator import ScraperOrchestrator
from src.models.product import ProductListPage


async def main() -> None:
    scraper = ScraperOrchestrator()
    result = await scraper.scrape(
        url="https://example.com",
        schema=ProductListPage,
        system_prompt=SYSTEM_PROMPT_ECOMMERCE,
        wait_until="domcontentloaded",
        full_page=True,
    )

    if result["success"]:
        products = result["data"].get("products", [])
        print(f"Produtos extraidos: {len(products)}")
        print(f"Custo: ${result['metadata']['cost_usd']:.4f}")
    else:
        print(f"Erro: {result.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())

