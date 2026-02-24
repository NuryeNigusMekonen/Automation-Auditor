# src/nodes/aggregator.py
from __future__ import annotations
from typing import Dict, List
from src.state import AgentState, Evidence


def evidence_aggregator(state: AgentState) -> Dict:
    """
    LangGraph reducers already merge, this node:
    - ensures each rubric dimension has an evidence list (possibly empty)
    - prepares a small "evidence_packet" for each criterion for judge prompts
    """
    dims = state.get("rubric_dimensions", [])
    evidences: Dict[str, List[Evidence]] = state.get("evidences", {})

    for d in dims:
        cid = d.get("id", "")
        if cid and cid not in evidences:
            evidences[cid] = []

    # Build a light packet (strings) per criterion
    packets: Dict[str, str] = {}
    for d in dims:
        cid = d.get("id", "")
        if not cid:
            continue
        evs = evidences.get(cid, [])
        lines = []
        for i, e in enumerate(evs[:12]):
            lines.append(
                f"- ev[{i}] goal={e.goal} found={e.found} loc={e.location} conf={e.confidence}\n"
                f"  rationale={e.rationale}\n"
                f"  content={_short(e.content)}"
            )
        packets[cid] = "\n".join(lines) if lines else "No evidence collected for this criterion."
    return {"evidences": evidences, "evidence_packets": packets}


def _short(s: str | None, n: int = 280) -> str:
    if not s:
        return ""
    t = s.replace("\n", " ").strip()
    return t[:n] + ("..." if len(t) > n else "")