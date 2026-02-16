"""Validacao de dados extraidos."""
from typing import Any

from pydantic import BaseModel, ValidationError


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


def _collect_url_flags(obj: Any, path: str = "") -> list[str]:
    flags: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            subpath = f"{path}.{key}" if path else key
            lowered = key.lower()
            if ("url" in lowered or "link" in lowered) and isinstance(value, str):
                if value and not value.startswith(("http://", "https://")):
                    flags.append(f"invalid_url:{subpath}")
            flags.extend(_collect_url_flags(value, subpath))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            flags.extend(_collect_url_flags(value, f"{path}[{idx}]"))
    return flags


def _coerce_guided_string_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Normaliza campos comuns do modo guiado para reduzir falhas de schema."""
    out = dict(data)
    for key in ("objective", "summary", "title", "description"):
        if key in out and out[key] is not None and not isinstance(out[key], str):
            out[key] = str(out[key])

    findings = out.get("findings")
    if isinstance(findings, list):
        normalized: list[Any] = []
        for item in findings:
            if isinstance(item, dict):
                item_copy = dict(item)
                if "title" in item_copy and item_copy["title"] is not None and not isinstance(item_copy["title"], str):
                    item_copy["title"] = str(item_copy["title"])
                if "description" in item_copy and item_copy["description"] is not None and not isinstance(item_copy["description"], str):
                    item_copy["description"] = str(item_copy["description"])
                
                # Coercao de URL: se for string vazia ou invalida, setar None para passar na validacao HttpUrl
                if "url" in item_copy and isinstance(item_copy["url"], str):
                    val = item_copy["url"].strip()
                    if not val or val.lower() in ("n/a", "none"):
                        item_copy["url"] = None
                    elif not val.startswith(("http://", "https://")):
                        # Se nao comeca com http, tenta consertar ou anula
                        if val.startswith("www."):
                            item_copy["url"] = f"https://{val}"
                        else:
                            # URL relativa ou lixo -> anula para nao falhar validacao
                            item_copy["url"] = None

                extra = item_copy.get("extra")
                if isinstance(extra, dict):
                    item_copy["extra"] = {str(k): (v if isinstance(v, (str, int, float, bool)) or v is None else str(v)) for k, v in extra.items()}
                normalized.append(item_copy)
            else:
                normalized.append(item)
        out["findings"] = normalized
    return out


class DataValidator:
    """Valida dados brutos com schema Pydantic."""

    @staticmethod
    def validate(
        data: dict[str, Any],
        schema: type[BaseModel],
    ) -> tuple[dict[str, Any] | None, list[str], dict[str, Any]]:
        try:
            parsed = schema(**data)
            dumped = parsed.model_dump()
            quality = DataValidator.assess_quality(dumped, schema=schema)
            return dumped, [], quality
        except ValidationError as exc:
            coerced = _coerce_guided_string_fields(data)
            try:
                parsed = schema(**coerced)
                dumped = parsed.model_dump()
                quality = DataValidator.assess_quality(dumped, schema=schema)
                quality["quality_flags"] = [*quality.get("quality_flags", []), "schema_coerced"]
                return dumped, [], quality
            except ValidationError:
                errors = [err["msg"] for err in exc.errors()]
                return None, errors, {"quality_score": 0.0, "quality_flags": ["schema_validation_error"]}

    @staticmethod
    def assess_quality(data: dict[str, Any], schema: type[BaseModel]) -> dict[str, Any]:
        """Calcula score simples de qualidade para dados validados."""
        flags: list[str] = []
        required = [name for name, field in schema.model_fields.items() if field.is_required()]
        required_total = max(len(required), 1)
        present_required = 0
        for field_name in required:
            value = data.get(field_name)
            if _is_empty(value):
                flags.append(f"missing_required:{field_name}")
            else:
                present_required += 1
        completeness_ratio = present_required / required_total

        url_flags = _collect_url_flags(data)
        flags.extend(url_flags)
        penalties = min(len(flags) * 0.08, 0.45)
        quality_score = max(round((completeness_ratio - penalties), 3), 0.0)
        return {
            "quality_score": quality_score,
            "quality_flags": flags,
            "required_total": required_total,
            "required_present": present_required,
        }

