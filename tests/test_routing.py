from src.nodes.routing import needs_more_evidence
from src.state import Evidence


def test_needs_more_evidence_blocks_when_required_key_missing() -> None:
    state = {
        "evidences": {
            "git_forensic_analysis": [
                Evidence(
                    goal="git_forensic_analysis",
                    found=True,
                    content="ok",
                    location="git log",
                    rationale="present",
                    confidence=1.0,
                )
            ]
        }
    }

    patch = needs_more_evidence(state)
    guard = patch["evidences"]["orchestration_guard"][0]
    assert guard.found is False
    assert "graph_orchestration" in (guard.content or "")


def test_needs_more_evidence_allows_negative_findings_if_key_exists() -> None:
    state = {
        "evidences": {
            "git_forensic_analysis": [
                Evidence(
                    goal="git_forensic_analysis",
                    found=False,
                    content="negative but present",
                    location="git log",
                    rationale="still evidence",
                    confidence=0.9,
                )
            ],
            "graph_orchestration": [
                Evidence(
                    goal="graph_orchestration",
                    found=False,
                    content="negative but present",
                    location="src/graph.py",
                    rationale="still evidence",
                    confidence=0.9,
                )
            ],
        }
    }

    patch = needs_more_evidence(state)
    assert patch == {}
