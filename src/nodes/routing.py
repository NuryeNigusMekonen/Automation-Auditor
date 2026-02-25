from __future__ import annotations

from typing import Dict, List

from src.state import AgentState, Evidence


REQUIRED_CRITERIA = [
    "git_forensic_analysis",
    "graph_orchestration",
]


def needs_more_evidence(state: AgentState) -> Dict:
    missing: List[str] = []
    for cid in REQUIRED_CRITERIA:
        evs = state["evidences"].get(cid, [])
        if not evs:
            missing.append(cid)
        elif any(e.found is False for e in evs):
            missing.append(cid)

    if not missing:
        return {}

    msg = "Missing required evidence: " + ", ".join(missing)
    return {
        "evidences": {
            "orchestration_guard": [
                Evidence(
                    goal="orchestration_guard",
                    found=False,
                    content=msg,
                    location="graph",
                    rationale="Guard node detected missing evidence before judge fan-out",
                    confidence=0.9,
                )
            ]
        }
    }


def route_after_aggregation(state: AgentState) -> str:
    evs = state["evidences"].get("orchestration_guard", [])
    if evs and any(e.found is False for e in evs):
        return "END"
    return "JUDGES"