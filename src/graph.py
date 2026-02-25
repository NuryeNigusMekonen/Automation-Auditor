# src/graph.py
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.state import AgentState
from src.nodes.aggregator import evidence_aggregator, opinions_aggregator
from src.nodes.detectives import doc_analyst, repo_investigator, vision_inspector
from src.nodes.judges import defense, prosecutor, tech_lead
from src.nodes.justice import chief_justice


def _route_after_evidence(state: AgentState) -> str:
    # Deterministic routing for missing artifacts or node failures.
    required = [
        "git_forensic_analysis",
        "graph_orchestration",
        "state_management_rigor",
        "safe_tool_engineering",
    ]

    missing: list[str] = []
    evidences = state.get("evidences", {}) or {}
    for cid in required:
        evs = evidences.get(cid, []) or []
        if not evs:
            missing.append(cid)
            continue
        if any(getattr(e, "found", True) is False for e in evs):
            missing.append(cid)

    return "missing_artifacts" if missing else "judges_fanout"


def _route_after_opinions(state: AgentState) -> str:
    # If judges produced no opinions, end early.
    ops = state.get("opinions", []) or []
    return "end" if len(ops) == 0 else "chief_justice"


def missing_artifacts(state: AgentState) -> dict:
    # Add a deterministic note to the report and end.
    required = [
        "git_forensic_analysis",
        "graph_orchestration",
        "state_management_rigor",
        "safe_tool_engineering",
    ]

    evidences = state.get("evidences", {}) or {}
    missing: list[str] = []
    for cid in required:
        evs = evidences.get(cid, []) or []
        if not evs or any(getattr(e, "found", True) is False for e in evs):
            missing.append(cid)

    msg = "Missing required evidence: " + ", ".join(missing) if missing else "No missing evidence."
    md = "\n".join(
        [
            "# Audit Report",
            "",
            "## Executive Summary",
            f"Repo: {state.get('repo_url','')}",
            "Overall score: 1.00 / 5.00",
            "",
            "## Early Exit",
            msg,
            "",
        ]
    )
    return {"final_report_markdown": [md]}


def build_graph():
    g = StateGraph(AgentState)

    # Detectives
    g.add_node("repo_investigator", repo_investigator)
    g.add_node("doc_analyst", doc_analyst)
    g.add_node("vision_inspector", vision_inspector)

    # Fan-in after detectives
    g.add_node("evidence_aggregator", evidence_aggregator)

    # Guard / missing artifacts path
    g.add_node("missing_artifacts", missing_artifacts)

    # Judges
    g.add_node("prosecutor", prosecutor)
    g.add_node("defense", defense)
    g.add_node("tech_lead", tech_lead)

    # Fan-in after judges
    g.add_node("opinions_aggregator", opinions_aggregator)

    # Chief Justice
    g.add_node("chief_justice", chief_justice)

    # Fan-out detectives from START
    g.add_edge(START, "repo_investigator")
    g.add_edge(START, "doc_analyst")
    g.add_edge(START, "vision_inspector")

    # Fan-in detectives
    g.add_edge("repo_investigator", "evidence_aggregator")
    g.add_edge("doc_analyst", "evidence_aggregator")
    g.add_edge("vision_inspector", "evidence_aggregator")

    # Conditional routing after evidence aggregation
    g.add_conditional_edges(
        "evidence_aggregator",
        _route_after_evidence,
        {
            "missing_artifacts": "missing_artifacts",
            "judges_fanout": "prosecutor",
        },
    )
    g.add_edge("evidence_aggregator", "defense")
    g.add_edge("evidence_aggregator", "tech_lead")

    # Fan-in judges
    g.add_edge("prosecutor", "opinions_aggregator")
    g.add_edge("defense", "opinions_aggregator")
    g.add_edge("tech_lead", "opinions_aggregator")

    # Conditional routing after opinions aggregation
    g.add_conditional_edges(
        "opinions_aggregator",
        _route_after_opinions,
        {
            "end": END,
            "chief_justice": "chief_justice",
        },
    )

    # Final synthesis
    g.add_edge("chief_justice", END)

    return g.compile()