"""Persistencia em banco e JSON."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    MetaData,
    String,
    Table,
    desc,
    select,
)
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.sql import text

from src.config.settings import settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]

metadata = MetaData()
scraping_results = Table(
    "scraping_results",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("url", String(2048), nullable=False),
    Column("domain", String(255), nullable=False, default=""),
    Column("created_at", DateTime, nullable=False),
    Column("success", Boolean, nullable=False, default=False),
    Column("error_type", String(64), nullable=False, default="unknown"),
    Column("cost_usd", Float, nullable=False),
    Column("payload", JSON, nullable=False),
)
Index("idx_scraping_results_url", scraping_results.c.url)
Index("idx_scraping_results_created_at", scraping_results.c.created_at)
Index("idx_scraping_results_success", scraping_results.c.success)

agent_executions = Table(
    "agent_executions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("url", String(2048), nullable=False),
    Column("goal", String(2048), nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("success", Boolean, nullable=False, default=False),
    Column("cost_usd", Float, nullable=False, default=0.0),
    Column("payload", JSON, nullable=False),
)
Index("idx_agent_executions_created_at", agent_executions.c.created_at)
Index("idx_agent_executions_success", agent_executions.c.success)

agent_steps = Table(
    "agent_steps",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("execution_id", Integer, nullable=False),
    Column("step_index", Integer, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("success", Boolean, nullable=False, default=False),
    Column("action", JSON, nullable=False),
    Column("state_snapshot", JSON, nullable=False),
    Column("error", String(2048), nullable=True),
)
Index("idx_agent_steps_execution_id", agent_steps.c.execution_id)
Index("idx_agent_steps_created_at", agent_steps.c.created_at)


class StorageManager:
    """Gerencia persistencia de resultados de scraping."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = self._normalize_database_url(database_url or settings.DATABASE_URL)
        self.engine: AsyncEngine = create_async_engine(self.database_url, echo=False)

    async def initialize(self) -> None:
        """Cria tabelas se nao existirem."""
        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
            await self._ensure_sqlite_columns(conn)

    async def save(self, data: dict[str, Any], metadata_obj: dict[str, Any]) -> int:
        """Salva resultado validado (atalho para save_attempt)."""
        payload = {"success": True, "data": data, "metadata": metadata_obj}
        return await self.save_attempt(
            payload=payload,
            url=str(metadata_obj.get("url", "")),
            cost_usd=float(metadata_obj.get("cost_usd", 0)),
        )

    async def save_attempt(
        self,
        payload: dict[str, Any],
        url: str,
        cost_usd: float = 0.0,
    ) -> int:
        """Salva qualquer tentativa de scraping (sucesso/erro)."""
        created_at = datetime.utcnow()
        safe_payload = self._normalize_for_json(payload)
        payload_metadata = safe_payload.get("metadata", {}) if isinstance(safe_payload, dict) else {}
        success = bool(safe_payload.get("success", False)) if isinstance(safe_payload, dict) else False
        error_type = (
            str(payload_metadata.get("error_type", "unknown"))
            if isinstance(payload_metadata, dict)
            else "unknown"
        )
        domain = self._extract_domain(url)

        async with self.engine.begin() as conn:
            result = await conn.execute(
                scraping_results.insert().values(
                    url=url,
                    domain=domain,
                    created_at=created_at,
                    success=success,
                    error_type=error_type,
                    cost_usd=float(cost_usd),
                    payload=safe_payload,
                )
            )
            record_id = int(result.inserted_primary_key[0])

        await self._save_json_backup(record_id=record_id, payload=safe_payload)
        return record_id

    async def _save_json_backup(self, record_id: int, payload: dict[str, Any]) -> None:
        export_dir = Path(settings.EXPORTS_DIR)
        if not export_dir.is_absolute():
            export_dir = PROJECT_ROOT / export_dir
        export_dir.mkdir(parents=True, exist_ok=True)

        out = {
            "record_id": record_id,
            "saved_at": datetime.utcnow().isoformat(),
            "payload": payload,
        }
        file_path = export_dir / f"scrape_{record_id}.json"
        file_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    async def list_recent(
        self,
        limit: int = 20,
        success: bool | None = None,
        domain: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista tentativas mais recentes."""
        safe_limit = max(1, min(limit, 200))
        stmt = select(scraping_results).order_by(desc(scraping_results.c.id)).limit(safe_limit)
        if success is not None:
            stmt = stmt.where(scraping_results.c.success == success)
        if domain:
            stmt = stmt.where(scraping_results.c.domain.contains(domain.strip().lower()))
        async with self.engine.begin() as conn:
            rows = (await conn.execute(stmt)).mappings()
            return [dict(row) for row in rows]

    async def save_agent_execution(
        self,
        url: str,
        goal: str,
        result_payload: dict[str, Any],
    ) -> int:
        created_at = datetime.utcnow()
        safe_payload = self._normalize_for_json(result_payload)
        success = bool(safe_payload.get("success", False)) if isinstance(safe_payload, dict) else False
        cost = (
            float((safe_payload.get("metadata", {}) or {}).get("cost_usd", 0))
            if isinstance(safe_payload, dict)
            else 0.0
        )
        async with self.engine.begin() as conn:
            result = await conn.execute(
                agent_executions.insert().values(
                    url=url,
                    goal=goal,
                    created_at=created_at,
                    success=success,
                    cost_usd=cost,
                    payload=safe_payload,
                )
            )
            return int(result.inserted_primary_key[0])

    async def save_agent_steps(self, execution_id: int, steps: list[dict[str, Any]]) -> None:
        now = datetime.utcnow()
        async with self.engine.begin() as conn:
            for step in steps:
                await conn.execute(
                    agent_steps.insert().values(
                        execution_id=execution_id,
                        step_index=int(step.get("step_index", 0)),
                        created_at=now,
                        success=bool(step.get("success", False)),
                        action=self._normalize_for_json(step.get("action", {})),
                        state_snapshot=self._normalize_for_json(step.get("state_snapshot", {})),
                        error=str(step.get("error")) if step.get("error") else None,
                    )
                )

    async def get_execution_steps(self, execution_id: int) -> list[dict[str, Any]]:
        stmt = (
            select(agent_steps)
            .where(agent_steps.c.execution_id == execution_id)
            .order_by(agent_steps.c.step_index.asc())
        )
        async with self.engine.begin() as conn:
            rows = (await conn.execute(stmt)).mappings()
            return [dict(row) for row in rows]

    def _normalize_for_json(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(k): self._normalize_for_json(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._normalize_for_json(v) for v in value]
        return str(value)

    def _normalize_database_url(self, raw_url: str) -> str:
        sqlite_prefixes = ("sqlite+aiosqlite:///", "sqlite:///")
        if not raw_url.startswith(sqlite_prefixes):
            return raw_url

        prefix = "sqlite+aiosqlite:///" if raw_url.startswith("sqlite+aiosqlite:///") else "sqlite:///"
        db_path_text = raw_url[len(prefix) :]
        db_path = Path(db_path_text)
        if not db_path.is_absolute():
            db_path = PROJECT_ROOT / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"{prefix}{db_path.as_posix()}"

    def _extract_domain(self, url: str) -> str:
        from urllib.parse import urlparse

        try:
            return (urlparse(url).netloc or "unknown").lower()
        except Exception:
            return "unknown"

    async def close(self) -> None:
        """Fecha engine SQLAlchemy."""
        await self.engine.dispose()

    async def _ensure_sqlite_columns(self, conn: Any) -> None:
        if not self.database_url.startswith("sqlite"):
            return
        rows = (await conn.execute(text("PRAGMA table_info(scraping_results)"))).mappings().all()
        existing = {row["name"] for row in rows}
        if "domain" not in existing:
            await conn.execute(text("ALTER TABLE scraping_results ADD COLUMN domain VARCHAR(255) DEFAULT ''"))
        if "success" not in existing:
            await conn.execute(text("ALTER TABLE scraping_results ADD COLUMN success BOOLEAN DEFAULT 0"))
        if "error_type" not in existing:
            await conn.execute(
                text("ALTER TABLE scraping_results ADD COLUMN error_type VARCHAR(64) DEFAULT 'unknown'")
            )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_scraping_results_url ON scraping_results (url)"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_scraping_results_created_at ON scraping_results (created_at)"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_scraping_results_success ON scraping_results (success)"
            )
        )
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS agent_executions ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "url VARCHAR(2048) NOT NULL, "
                "goal VARCHAR(2048) NOT NULL, "
                "created_at DATETIME NOT NULL, "
                "success BOOLEAN NOT NULL DEFAULT 0, "
                "cost_usd FLOAT NOT NULL DEFAULT 0, "
                "payload JSON NOT NULL)"
            )
        )
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS agent_steps ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "execution_id INTEGER NOT NULL, "
                "step_index INTEGER NOT NULL, "
                "created_at DATETIME NOT NULL, "
                "success BOOLEAN NOT NULL DEFAULT 0, "
                "action JSON NOT NULL, "
                "state_snapshot JSON NOT NULL, "
                "error VARCHAR(2048))"
            )
        )
        await conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_agent_executions_created_at ON agent_executions (created_at)")
        )
        await conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_agent_executions_success ON agent_executions (success)")
        )
        await conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_agent_steps_execution_id ON agent_steps (execution_id)")
        )
        await conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_agent_steps_created_at ON agent_steps (created_at)")
        )

