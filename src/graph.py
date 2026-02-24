## Goal
# Create a StateGraph that compiles.

## Checklist
# StateGraph built with AgentState
# Add nodes, even stub nodes
# Wire START to END through nodes
# Compile graph

## Output
# graph.invoke returns state with final_report field.
# src/graph.py
from __future__ import annotations
from langgraph.graph import StateGraph, START, END
from src.state import AgentState

from src.nodes.detectives import repo_investigator, doc_analyst
from src.nodes.aggregator import evidence_aggregator
from src.nodes.judges import prosecutor_node, defense_node, techlead_node
from src.nodes.justice import chief_justice


def build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    # Layer 1: Detectives (parallel)
    g.add_node("repo_investigator", repo_investigator)
    g.add_node("doc_analyst", doc_analyst)

    # Fan-in
    g.add_node("evidence_aggregator", evidence_aggregator)

    # Layer 2: Judges (parallel)
    g.add_node("prosecutor", prosecutor_node)
    g.add_node("defense", defense_node)
    g.add_node("techlead", techlead_node)

    # Layer 3: Chief Justice
    g.add_node("chief_justice", chief_justice)

    # Wiring
    g.add_edge(START, "repo_investigator")
    g.add_edge(START, "doc_analyst")

    g.add_edge("repo_investigator", "evidence_aggregator")
    g.add_edge("doc_analyst", "evidence_aggregator")

    g.add_edge("evidence_aggregator", "prosecutor")
    g.add_edge("evidence_aggregator", "defense")
    g.add_edge("evidence_aggregator", "techlead")

    g.add_edge("prosecutor", "chief_justice")
    g.add_edge("defense", "chief_justice")
    g.add_edge("techlead", "chief_justice")

    g.add_edge("chief_justice", END)

    return g.compile()