"""Buffer de evidencias multi-step com deduplicacao simples."""
from typing import Any


class ExtractionBuffer:
    """Acumula evidencias e itens extraidos ao longo dos passos."""

    def __init__(self) -> None:
        self.states: list[dict[str, Any]] = []
        self.items: list[dict[str, Any]] = []

    def add_state(self, state: dict[str, Any]) -> None:
        self.states.append(state)

    def add_items(self, items: list[dict[str, Any]]) -> None:
        for item in items:
            if self._is_new(item):
                self.items.append(item)

    def _is_new(self, item: dict[str, Any]) -> bool:
        key = self._semantic_key(item)
        existing = {self._semantic_key(i) for i in self.items}
        return key not in existing

    def _semantic_key(self, item: dict[str, Any]) -> str:
        name = str(item.get("title") or item.get("name") or "").strip().lower()
        addr = str(item.get("address") or item.get("location") or "").strip().lower()
        phone = str(item.get("phone") or "").strip().lower()
        return f"{name}|{addr}|{phone}"

