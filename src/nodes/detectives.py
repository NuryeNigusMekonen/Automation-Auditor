from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from src.state import AgentState, Evidence
from src.tools.ast_tools import analyze_graph_structure
from src.tools.git_tools import clone_repo_sandboxed, extract_git_history
from src.tools.pdf_tools import (
    ingest_pdf_chunks,
    extract_keyword_evidence,
    extract_report_paths_evidence,
)
from src.tools.repo_scan_tools import scan_for_os_system
from src.tools.vision_tools import analyze_pdf_diagrams_safe


def repo_investigator(state: AgentState) -> Dict:
    repo_url = state["repo_url"]
    repo_path = clone_repo_sandboxed(repo_url)

    git_evs: List[Evidence] = extract_git_history(repo_path)
    graph_evs: List[Evidence] = analyze_graph_structure(repo_path)

    root = Path(repo_path)
    state_file = root / "src" / "state.py"
    judge_file = root / "src" / "nodes" / "judges.py"
    justice_file = root / "src" / "nodes" / "justice.py"

    state_presence: List[Evidence] = [
        Evidence(
            goal="state_management_rigor",
            found=state_file.exists(),
            content=str(state_file) if state_file.exists() else None,
            location=str(state_file) if state_file.exists() else "repo",
            rationale="Presence check for typed state definitions and reducers",
            confidence=0.8,
        )
    ]

    structured_presence: List[Evidence] = [
        Evidence(
            goal="structured_output_enforcement",
            found=judge_file.exists(),
            content=str(judge_file) if judge_file.exists() else None,
            location=str(judge_file) if judge_file.exists() else "repo",
            rationale="Presence check for judge nodes and structured output enforcement",
            confidence=0.8,
        )
    ]

    justice_presence: List[Evidence] = [
        Evidence(
            goal="chief_justice_synthesis",
            found=justice_file.exists(),
            content=str(justice_file) if justice_file.exists() else None,
            location=str(justice_file) if justice_file.exists() else "repo",
            rationale="Presence check for chief justice synthesis node",
            confidence=0.8,
        )
    ]

    try:
        safe_evs: List[Evidence] = scan_for_os_system(repo_path)
    except Exception as e:
        safe_evs = [
            Evidence(
                goal="safe_tool_engineering",
                found=False,
                content=str(e),
                location="auditor",
                rationale="Safety scan failed in auditor runtime",
                confidence=0.6,
            )
        ]

    return {
        "evidences": {
            "git_forensic_analysis": git_evs,
            "graph_orchestration": graph_evs,
            "state_management_rigor": state_presence,
            "structured_output_enforcement": structured_presence,
            "chief_justice_synthesis": justice_presence,
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