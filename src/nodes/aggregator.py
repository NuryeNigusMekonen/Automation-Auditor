from __future__ import annotations

from typing import Dict

from src.state import AgentState


def evidence_aggregator(state: AgentState) -> Dict:
    # evidences already merged by reducers
    return {}


def opinions_aggregator(state: AgentState) -> Dict:
    # opinions already merged by reducers
    return {}