
import asyncio
import os
import sys

# Adiciona o diretório raiz ao path para importar módulos do src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from src.config.settings import settings

async def clear_database():
    print(f"Connecting to database: {settings.DATABASE_URL}")
    engine = create_async_engine(settings.DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        print("Clearing scraping_results...")
        await conn.execute(text("DELETE FROM scraping_results"))
        
        print("Clearing agent_executions...")
        await conn.execute(text("DELETE FROM agent_executions"))
        
        print("Clearing agent_steps...")
        await conn.execute(text("DELETE FROM agent_steps"))
        
    print("Database cleared successfully.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(clear_database())
