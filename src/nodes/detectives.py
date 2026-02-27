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
    query_pdf_evidence,
)
from src.tools.repo_scan_tools import scan_for_os_system
from src.tools.state_tools import inspect_state_models
from src.tools.vision_tools import analyze_pdf_diagrams_safe



def repo_investigator(state: AgentState) -> Dict:
    repo_url = state["repo_url"]

    try:
        repo_path = clone_repo_sandboxed(repo_url, state["workspace_dir"])
    except Exception as e:
        return {
            "evidences": {
                "git_forensic_analysis": [
                    Evidence(
                        goal="git_forensic_analysis",
                        found=False,
                        content=f"Clone failed: {e}",
                        location="git clone",
                        rationale="Repo clone failure blocks git and AST inspection",
                        confidence=0.95,
                    )
                ],
                "graph_orchestration": [
                    Evidence(
                        goal="graph_orchestration",
                        found=False,
                        content="Clone failed. No graph inspection.",
                        location="repo",
                        rationale="Repo not available for AST",
                        confidence=0.9,
                    )
                ],
                "state_management_rigor": [
                    Evidence(
                        goal="state_management_rigor",
                        found=False,
                        content="Clone failed. No state inspection.",
                        location="repo",
                        rationale="Repo not available for state checks",
                        confidence=0.9,
                    )
                ],
                "safe_tool_engineering": [
                    Evidence(
                        goal="safe_tool_engineering",
                        found=False,
                        content="Clone failed. No safety scan.",
                        location="repo",
                        rationale="Repo not available for tool scan",
                        confidence=0.9,
                    )
                ],
            }
        }

    root = Path(repo_path)
    judge_file = root / "src" / "nodes" / "judges.py"
    justice_file = root / "src" / "nodes" / "justice.py"

    def rel(p: Path) -> str:
        return p.relative_to(root).as_posix()

    git_evs: List[Evidence] = extract_git_history(repo_path)
    graph_evs: List[Evidence] = analyze_graph_structure(repo_path)
    state_evs: List[Evidence] = inspect_state_models(repo_path)

    structured_presence: List[Evidence] = [
        Evidence(
            goal="structured_output_enforcement",
            found=judge_file.exists(),
            content=rel(judge_file) if judge_file.exists() else None,
            location=(rel(judge_file) if judge_file.exists() else "repo"),
            rationale="Presence check for judge nodes and structured output enforcement",
            confidence=0.8,
        )
    ]

    justice_presence: List[Evidence] = [
        Evidence(
            goal="chief_justice_synthesis",
            found=justice_file.exists(),
            content=rel(justice_file) if justice_file.exists() else None,
            location=(rel(justice_file) if justice_file.exists() else "repo"),
            rationale="Presence check for chief justice synthesis node",
            confidence=0.8,
        )
    ]

    judge_text = None
    if judge_file.exists():
        try:
            judge_text = judge_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            judge_text = None

    persona_snip = judge_text[:2000] if judge_text else None
    judicial_nuance_evs: List[Evidence] = [
        Evidence(
            goal="judicial_nuance",
            found=bool(judge_text),
            content=persona_snip,
            location=(rel(judge_file) if judge_file.exists() else "repo"),
            rationale="Provide prompt evidence for persona separation scoring",
            confidence=0.85,
        )
    ]

    try:
        safe_evs: List[Evidence] = scan_for_os_system(repo_path)
    except Exception as e:
        safe_evs = [
            Evidence(
                goal="safe_tool_engineering",
                found=False,
                content=f"Safety scan failed: {e}",
                location="auditor",
                rationale="Safety scan failed in runtime",
                confidence=0.7,
            )
        ]

    repo_files: List[str] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        sp = str(p)
        if "/.venv/" in sp or "/venv/" in sp or "__pycache__" in sp or "/.git/" in sp:
            continue
        repo_files.append(p.relative_to(root).as_posix())

    file_index_ev = Evidence(
        goal="repo_file_index",
        found=True,
        content="\n".join(sorted(repo_files)[:20000]),
        location="repo_index",
        rationale="Repo file index for PDF cross reference",
        confidence=0.9,
    )

    return {
        "evidences": {
            "git_forensic_analysis": git_evs,
            "graph_orchestration": graph_evs,
            "state_management_rigor": state_evs,
            "structured_output_enforcement": structured_presence,
            "chief_justice_synthesis": justice_presence,
            "safe_tool_engineering": safe_evs,
            "repo_file_index": [file_index_ev],
            "judicial_nuance": judicial_nuance_evs,
        }
    }


def doc_analyst(state: AgentState) -> Dict:
    pdf_path = state["pdf_path"]
    try:
        chunks = ingest_pdf_chunks(pdf_path)
    except Exception as e:
        return {
            "evidences": {
                "theoretical_depth": [
                    Evidence(
                        goal="theoretical_depth",
                        found=False,
                        content=f"PDF read failed: {e}",
                        location="pdf",
                        rationale="PDF parsing failure blocks theoretical depth checks",
                        confidence=0.9,
                    )
                ],
                "report_accuracy": [
                    Evidence(
                        goal="report_accuracy",
                        found=False,
                        content="PDF read failed. No path extraction.",
                        location="pdf",
                        rationale="PDF parsing failure blocks cross reference",
                        confidence=0.9,
                    )
                ],
            }
        }

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

    paths_evs: List[Evidence] = extract_report_paths_evidence(chunks, goal="report_accuracy")

    snip_evs: List[Evidence] = []
    for q in [
        "Dialectical Synthesis implementation",
        "Fan-In Fan-Out in StateGraph",
        "Metacognition how implemented",
        "State Synchronization reducer operator.add operator.ior",
    ]:
        snip_evs.extend(query_pdf_evidence(chunks, q, goal="theoretical_depth_snippets", top_k=2))

    return {
        "evidences": {
            "theoretical_depth": depth_evs,
            "theoretical_depth_snippets": snip_evs,
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