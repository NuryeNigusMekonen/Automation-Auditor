from src.nodes.judges import prosecutor
from src.state import Evidence


def test_offline_mode_skips_llm_and_returns_deterministic_opinion():
    state = {
        "offline_mode": True,
        "rubric_dimensions": [
            {
                "id": "safe_tool_engineering",
                "name": "Safe Tool Engineering",
                "forensic_instruction": "inspect",
                "success_pattern": "safe",
                "failure_pattern": "unsafe",
            }
        ],
        "evidences": {
            "safe_tool_engineering": [
                Evidence(
                    goal="safe_tool_engineering",
                    found=True,
                    content="ok",
                    location="src/tools",
                    rationale="scan",
                    confidence=0.9,
                )
            ],
            "citation_pool": [
                Evidence(
                    goal="citation_pool",
                    found=True,
                    content="src/tools",
                    location="src/nodes/aggregator.py",
                    rationale="pool",
                    confidence=0.9,
                )
            ],
        },
    }

    out = prosecutor(state)
    opinion = out["opinions"][0]
    assert opinion.judge == "Prosecutor"
    assert opinion.criterion_id == "safe_tool_engineering"
    assert 1 <= opinion.score <= 5
    assert "risk" in opinion.argument
