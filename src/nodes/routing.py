from __future__ import annotations

from typing import Dict, List

from src.state import AgentState, Evidence


REQUIRED_CRITERIA = [
    "git_forensic_analysis",
    "graph_orchestration",
]


def needs_more_evidence(state: AgentState) -> Dict:
    """
    Guard node.

    Block judges only when required evidence keys are missing entirely.
    Do NOT block when evidence exists but found=False, because negative findings
    are still valid evidence for judges to score against.
    """
    missing: List[str] = []

    evidences = state.get("evidences", {}) or {}
    for cid in REQUIRED_CRITERIA:
        evs = evidences.get(cid, [])
        if not evs:
            missing.append(cid)

    if not missing:
        return {}

    msg = "Missing required evidence keys: " + ", ".join(missing)
    return {
        "evidences": {
            "orchestration_guard": [
                Evidence(
                    goal="orchestration_guard",
                    found=False,
                    content=msg,
                    location="src/nodes/routing.py",
                    rationale="Required evidence key absent. Judges would be scoring without baseline facts.",
                    confidence=0.9,
                )
            ]
        }
    }