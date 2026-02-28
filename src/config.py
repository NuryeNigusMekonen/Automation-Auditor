from __future__ import annotations

import json
import os
from typing import Any

from pydantic import BaseModel, Field


RUBRIC_REQUIRED_DIMENSION_KEYS = {
    "id",
    "name",
    "forensic_instruction",
    "success_pattern",
    "failure_pattern",
}

RUBRIC_REQUIRED_SYNTHESIS_KEYS = {
    "security_override",
    "fact_supremacy",
    "functionality_weight",
    "dissent_requirement",
    "variance_re_evaluation",
}


def _parse_env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    s = raw.strip().lower()
    if s in {"1", "true", "yes", "on"}:
        return True
    if s in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean env {name}={raw!r}")


def _parse_env_int(
    name: str,
    default: int,
    *,
    min_value: int = 1,
    max_value: int = 50000,
) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid integer env {name}={raw!r}") from exc
    if value < min_value or value > max_value:
        raise ValueError(
            f"Out-of-range env {name}={value}, expected [{min_value}, {max_value}]"
        )
    return value


class RuntimeConfig(BaseModel):
    enable_vision: bool
    offline_mode: bool
    verbose_logging: bool = False
    log_file_path: str | None = None

    cap_locations: int = Field(ge=1, le=2000)
    cap_report_paths: int = Field(ge=1, le=50000)
    cap_crossref_per_type: int = Field(ge=1, le=5000)
    cap_security_locations: int = Field(ge=1, le=2000)
    cap_security_snippets: int = Field(ge=1, le=2000)
    cap_security_signal_snippets: int = Field(ge=1, le=500)
    cap_allowed_citations: int = Field(ge=1, le=2000)
    cap_cited_evidence: int = Field(ge=1, le=200)
    cap_evidence_items: int = Field(ge=1, le=5000)

    @classmethod
    def from_sources(
        cls,
        *,
        enable_vision: bool,
        offline_mode: bool,
        verbose_logging: bool = False,
        log_file_path: str | None = None,
    ) -> "RuntimeConfig":
        return cls(
            enable_vision=enable_vision,
            offline_mode=offline_mode or _parse_env_bool("AUDITOR_OFFLINE_MODE", False),
            verbose_logging=verbose_logging
            or _parse_env_bool("AUDITOR_VERBOSE_LOGGING", False),
            log_file_path=log_file_path or os.getenv("AUDITOR_LOG_FILE"),
            cap_locations=_parse_env_int("AUDITOR_CAP_LOCATIONS", 50, max_value=2000),
            cap_report_paths=_parse_env_int(
                "AUDITOR_CAP_REPORT_PATHS", 2000, max_value=50000
            ),
            cap_crossref_per_type=_parse_env_int(
                "AUDITOR_CAP_CROSSREF_PER_TYPE", 200, max_value=5000
            ),
            cap_security_locations=_parse_env_int(
                "AUDITOR_CAP_SECURITY_LOCATIONS", 50, max_value=2000
            ),
            cap_security_snippets=_parse_env_int(
                "AUDITOR_CAP_SECURITY_SNIPPETS", 50, max_value=2000
            ),
            cap_security_signal_snippets=_parse_env_int(
                "AUDITOR_CAP_SECURITY_SIGNAL_SNIPPETS", 25, max_value=500
            ),
            cap_allowed_citations=_parse_env_int(
                "AUDITOR_CAP_ALLOWED_CITATIONS", 50, max_value=2000
            ),
            cap_cited_evidence=_parse_env_int(
                "AUDITOR_CAP_CITED_EVIDENCE", 12, max_value=200
            ),
            cap_evidence_items=_parse_env_int(
                "AUDITOR_CAP_EVIDENCE_ITEMS", 80, max_value=5000
            ),
        )


def validate_rubric_schema(obj: dict[str, Any]) -> None:
    dimensions = obj.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        raise ValueError("rubric.dimensions must be a non-empty list")

    for idx, dim in enumerate(dimensions):
        if not isinstance(dim, dict):
            raise ValueError(f"rubric.dimensions[{idx}] must be an object")
        missing = sorted(RUBRIC_REQUIRED_DIMENSION_KEYS - set(dim.keys()))
        if missing:
            raise ValueError(
                f"rubric.dimensions[{idx}] missing required keys: {', '.join(missing)}"
            )
        for key in RUBRIC_REQUIRED_DIMENSION_KEYS:
            val = dim.get(key)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(
                    f"rubric.dimensions[{idx}].{key} must be a non-empty string"
                )

    synthesis_rules = obj.get("synthesis_rules")
    if not isinstance(synthesis_rules, dict):
        raise ValueError("rubric.synthesis_rules must be an object")

    missing_rules = sorted(RUBRIC_REQUIRED_SYNTHESIS_KEYS - set(synthesis_rules.keys()))
    if missing_rules:
        raise ValueError(
            "rubric.synthesis_rules missing required keys: " + ", ".join(missing_rules)
        )


def load_rubric_dimensions(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError("rubric root must be an object")
    validate_rubric_schema(obj)
    return list(obj["dimensions"])
