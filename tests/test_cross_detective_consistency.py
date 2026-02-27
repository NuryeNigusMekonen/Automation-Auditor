from src.nodes.aggregator import evidence_aggregator
from src.state import Evidence


def test_cross_detective_consistency_positive_alignment() -> None:
    state = {
        "evidences": {
            "git_forensic_analysis": [
                Evidence(
                    goal="git_forensic_analysis",
                    found=True,
                    content="iterative commits",
                    location="git log",
                    rationale="history",
                    confidence=0.9,
                )
            ],
            "graph_orchestration": [
                Evidence(
                    goal="graph_orchestration",
                    found=True,
                    content="parallel fan-out",
                    location="src/graph.py",
                    rationale="ast",
                    confidence=0.9,
                )
            ],
        }
    }

    patch = evidence_aggregator(state)
    ev = patch["evidences"]["cross_detective_consistency"][0]
    assert ev.found is True
    assert "git_positive=true" in (ev.content or "")
    assert "graph_positive=true" in (ev.content or "")


def test_cross_detective_consistency_flags_report_hallucinations() -> None:
    state = {
        "evidences": {
            "report_accuracy": [
                Evidence(
                    goal="report_accuracy",
                    found=False,
                    content=None,
                    location="src/missing.py",
                    rationale="hallucinated path",
                    confidence=0.9,
                )
            ]
        }
    }

    patch = evidence_aggregator(state)
    ev = patch["evidences"]["cross_detective_consistency"][0]
    assert ev.found is False
    assert "report_hallucinations=true" in (ev.content or "")
