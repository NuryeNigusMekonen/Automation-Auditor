from src.nodes.justice import chief_justice
from src.state import Evidence, JudicialOpinion


def _dims() -> list[dict]:
    return [
        {
            "id": "safe_tool_engineering",
            "name": "Safe Tool Engineering",
            "failure_pattern": "unsafe shell",
        },
        {
            "id": "graph_orchestration",
            "name": "Graph Orchestration",
            "failure_pattern": "missing fan-in",
        },
    ]


def test_evidence_missing_caps_criterion_score_to_two() -> None:
    state = {
        "repo_url": "https://github.com/example/repo",
        "rubric_dimensions": _dims(),
        "evidences": {
            "safe_tool_engineering": [
                Evidence(
                    goal="safe_tool_engineering",
                    found=False,
                    content="missing",
                    location="src/tools",
                    rationale="missing",
                    confidence=0.9,
                )
            ],
            "graph_orchestration": [
                Evidence(
                    goal="graph_orchestration",
                    found=True,
                    content="ok",
                    location="src/graph.py",
                    rationale="ok",
                    confidence=0.9,
                )
            ],
        },
        "opinions": [
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="safe_tool_engineering",
                score=5,
                argument="risk",
                cited_evidence=["src/tools"],
            ),
            JudicialOpinion(
                judge="TechLead",
                criterion_id="safe_tool_engineering",
                score=5,
                argument="maintainability",
                cited_evidence=["src/tools"],
            ),
        ],
    }

    out = chief_justice(state)
    md = out["final_report_markdown"]
    assert "### Safe Tool Engineering (safe_tool_engineering)" in md
    assert "Final score: 2 / 5" in md


def test_security_cap_applies_only_with_signal_and_prosecutor_confirmation() -> None:
    base_opinions = [
        JudicialOpinion(
            judge="Prosecutor",
            criterion_id="safe_tool_engineering",
            score=2,
            argument="risk",
            cited_evidence=["src/tools"],
        ),
        JudicialOpinion(
            judge="TechLead",
            criterion_id="safe_tool_engineering",
            score=5,
            argument="maintainability",
            cited_evidence=["src/tools"],
        ),
        JudicialOpinion(
            judge="Defense",
            criterion_id="graph_orchestration",
            score=5,
            argument="effort",
            cited_evidence=["src/graph.py"],
        ),
    ]

    state_with_signal = {
        "repo_url": "https://github.com/example/repo",
        "rubric_dimensions": _dims(),
        "evidences": {
            "safe_tool_engineering": [
                Evidence(
                    goal="safe_tool_engineering",
                    found=True,
                    content="scan",
                    location="src/tools",
                    rationale="scan",
                    confidence=0.9,
                )
            ],
            "graph_orchestration": [
                Evidence(
                    goal="graph_orchestration",
                    found=True,
                    content="ok",
                    location="src/graph.py",
                    rationale="ok",
                    confidence=0.9,
                )
            ],
            "security_override_signal": [
                Evidence(
                    goal="security_override_signal",
                    found=True,
                    content="unsafe",
                    location="src/tools",
                    rationale="derived",
                    confidence=0.95,
                )
            ],
        },
        "opinions": base_opinions,
    }

    state_without_signal = {
        **state_with_signal,
        "evidences": {
            **state_with_signal["evidences"],
            "security_override_signal": [
                Evidence(
                    goal="security_override_signal",
                    found=False,
                    content="none",
                    location="src/tools",
                    rationale="derived",
                    confidence=0.95,
                )
            ],
        },
    }

    out_with = chief_justice(state_with_signal)
    out_without = chief_justice(state_without_signal)

    assert out_with["final_report"]["overall_score"] <= 3.0
    assert out_without["final_report"]["overall_score"] > 3.0
