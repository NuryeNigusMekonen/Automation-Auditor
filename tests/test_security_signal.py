from src.nodes.aggregator import evidence_aggregator
from src.state import Evidence


def test_security_override_signal_detected():
    state = {
        "evidences": {
            "safe_tool_engineering": [
                Evidence(
                    goal="safe_tool_engineering",
                    found=False,
                    content="Unsafe usage detected:\nfile.py",
                    location="src/tools",
                    rationale="",
                    confidence=1.0,
                )
            ]
        }
    }
    patch = evidence_aggregator(state)
    evs = patch["evidences"]["security_override_signal"]
    assert evs[0].found is True
