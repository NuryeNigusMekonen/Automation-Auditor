from __future__ import annotations

from typing import Dict, List

from src.state import AgentState, Evidence
from src.tools.git_tools import clone_repo_sandboxed, extract_git_history
from src.tools.ast_tools import analyze_graph_structure
from src.tools.pdf_tools import ingest_pdf_chunks, extract_keyword_evidence, extract_report_paths_evidence
from src.tools.vision_tools import analyze_pdf_diagrams_safe
from src.tools.repo_scan_tools import scan_state_management, scan_safe_tooling

def repo_investigator(state: AgentState) -> Dict:
    repo_url = state["repo_url"]
    repo_path = clone_repo_sandboxed(repo_url)

    git_evs: List[Evidence] = extract_git_history(repo_path)
    graph_evs: List[Evidence] = analyze_graph_structure(repo_path)
    state_evs: List[Evidence] = scan_state_management(repo_path)
    safe_evs: List[Evidence] = scan_safe_tooling(repo_path)

    return {
        "evidences": {
            "git_forensic_analysis": git_evs,
            "graph_orchestration": graph_evs,
            "state_management_rigor": state_evs,
            "safe_tool_engineering": safe_evs,
        }
    }


def doc_analyst(state: AgentState) -> Dict:
    pdf_path = state["pdf_path"]
    chunks = ingest_pdf_chunks(pdf_path)

    depth_evs: List[Evidence] = extract_keyword_evidence(
        chunks,
        keywords=[
            "Dialectical Synthesis",
            "Fan-In",
            "Fan-Out",
            "Metacognition",
            "State Synchronization",
        ],
        goal="theoretical_depth",
    )

    paths_evs: List[Evidence] = extract_report_paths_evidence(
        chunks,
        goal="report_accuracy",
    )

    return {
        "evidences": {
            "theoretical_depth": depth_evs,
            "report_accuracy": paths_evs,
        }
    }


def vision_inspector(state: AgentState) -> Dict:
    if not state.get("enable_vision", False):
        return {
            "evidences": {
                "swarm_visual": [
                    Evidence(
                        goal="swarm_visual",
                        found=False,
                        content=None,
                        location="vision",
                        rationale="Vision disabled. Skipped diagram analysis.",
                        confidence=1.0,
                    )
                ]
            }
        }

    pdf_path = state["pdf_path"]
    evs = analyze_pdf_diagrams_safe(pdf_path)
    return {"evidences": {"swarm_visual": evs}}