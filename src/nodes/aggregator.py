import json
from typing import Dict, List

from src.state import AgentState, Evidence


def evidence_aggregator(state: AgentState) -> AgentState:
    """
    Fan-in node.
    Builds short evidence packets per criterion for the judges.
    """
    packets: Dict[str, str] = {}
    evidences: Dict[str, List[Evidence]] = state.get("evidences", {})

    for criterion_id, ev_list in evidences.items():
        parts: List[dict] = []
        for ev in ev_list:
            parts.append(
                {
                    "goal": ev.goal,
                    "found": ev.found,
                    "location": ev.location,
                    "confidence": ev.confidence,
                    "content": (ev.content[:2000] if ev.content else None),
                }
            )
        packets[criterion_id] = json.dumps({"criterion_id": criterion_id, "evidence": parts}, indent=2)

    state["evidence_packets"] = packets
    return state