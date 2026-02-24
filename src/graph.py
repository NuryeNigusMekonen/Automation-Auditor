from langgraph.graph import StateGraph, START, END

from src.state import AgentState
from src.nodes.detectives import repo_investigator, doc_analyst, vision_inspector
from src.nodes.aggregator import evidence_aggregator
from src.nodes.judges import prosecutor_node, defense_node, techlead_node
from src.nodes.justice import chief_justice


def build_graph():
    g = StateGraph(AgentState)

    # Detectives
    g.add_node("repo_investigator", repo_investigator)
    g.add_node("doc_analyst", doc_analyst)
    g.add_node("vision_inspector", vision_inspector)

    # Fan-in
    g.add_node("evidence_aggregator", evidence_aggregator)

    # Judges
    g.add_node("prosecutor", prosecutor_node)
    g.add_node("defense", defense_node)
    g.add_node("techlead", techlead_node)

    # Supreme Court
    g.add_node("chief_justice", chief_justice)

    # Fan-out from START to detectives
    g.add_edge(START, "repo_investigator")
    g.add_edge(START, "doc_analyst")
    g.add_edge(START, "vision_inspector")

    # Fan-in to aggregator
    g.add_edge("repo_investigator", "evidence_aggregator")
    g.add_edge("doc_analyst", "evidence_aggregator")
    g.add_edge("vision_inspector", "evidence_aggregator")

    # Fan-out to judges
    g.add_edge("evidence_aggregator", "prosecutor")
    g.add_edge("evidence_aggregator", "defense")
    g.add_edge("evidence_aggregator", "techlead")

    # Fan-in to chief justice
    g.add_edge("prosecutor", "chief_justice")
    g.add_edge("defense", "chief_justice")
    g.add_edge("techlead", "chief_justice")

    g.add_edge("chief_justice", END)

    return g.compile()