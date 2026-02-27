import json

import pytest

from src.config import RuntimeConfig, load_rubric_dimensions, validate_rubric_schema


def test_runtime_config_rejects_invalid_int_env(monkeypatch):
    monkeypatch.setenv("AUDITOR_CAP_REPORT_PATHS", "oops")
    with pytest.raises(ValueError):
        RuntimeConfig.from_sources(enable_vision=False, offline_mode=False)


def test_rubric_schema_validation_missing_required_keys():
    bad = {
        "dimensions": [{"id": "x", "name": "n"}],
        "synthesis_rules": {
            "security_override": "x",
            "fact_supremacy": "x",
            "functionality_weight": "x",
            "dissent_requirement": "x",
            "variance_re_evaluation": "x",
        },
    }
    with pytest.raises(ValueError):
        validate_rubric_schema(bad)


def test_load_rubric_dimensions_valid(tmp_path):
    path = tmp_path / "rubric.json"
    path.write_text(
        json.dumps(
            {
                "dimensions": [
                    {
                        "id": "graph_orchestration",
                        "name": "Graph",
                        "forensic_instruction": "inspect",
                        "success_pattern": "parallel",
                        "failure_pattern": "linear",
                    }
                ],
                "synthesis_rules": {
                    "security_override": "rule",
                    "fact_supremacy": "rule",
                    "functionality_weight": "rule",
                    "dissent_requirement": "rule",
                    "variance_re_evaluation": "rule",
                },
            }
        ),
        encoding="utf-8",
    )

    dims = load_rubric_dimensions(str(path))
    assert len(dims) == 1
    assert dims[0]["id"] == "graph_orchestration"
