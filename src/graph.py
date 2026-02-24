from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.state import AgentState
from src.nodes.aggregator import evidence_aggregator, opinions_aggregator
from src.nodes.detectives import doc_analyst, repo_investigator, vision_inspector
from src.nodes.judges import defense, prosecutor, tech_lead
from src.nodes.justice import chief_justice


def build_graph():
    g = StateGraph(AgentState)

    # Detectives
    g.add_node("repo_investigator", repo_investigator)
    g.add_node("doc_analyst", doc_analyst)
    g.add_node("vision_inspector", vision_inspector)

    # Fan-in after detectives
    g.add_node("evidence_aggregator", evidence_aggregator)

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

    # Fan-out judges
    g.add_edge("evidence_aggregator", "prosecutor")
    g.add_edge("evidence_aggregator", "defense")
    g.add_edge("evidence_aggregator", "tech_lead")

    # Fan-in judges
    g.add_edge("prosecutor", "opinions_aggregator")
    g.add_edge("defense", "opinions_aggregator")
    g.add_edge("tech_lead", "opinions_aggregator")

    # Final synthesis
    g.add_edge("opinions_aggregator", "chief_justice")
    g.add_edge("chief_justice", END)

    return g.compile()