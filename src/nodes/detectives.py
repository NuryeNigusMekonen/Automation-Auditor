## Goal
# RepoInvestigator and DocAnalyst nodes that populate evidences.
# src/nodes/detectives.py
from __future__ import annotations
from typing import Dict, List
from src.state import AgentState, Evidence
from src.tools.git_tools import (
    clone_repo,
    extract_git_history,
    list_repo_files,
    scan_for_unsafe_os_system,
)
from src.tools.ast_tools import analyze_graph_structure
from src.tools.pdf_tools import ingest_pdf, search_chunks


def repo_investigator(state: AgentState) -> Dict:
    repo_url = state["repo_url"]
    repo_path, workdir = clone_repo(repo_url)

    # Basic structure checks
    files = set(list_repo_files(repo_path))
    state_file_exists = ("src/state.py" in files) or ("src/state.py".replace("\\", "/") in files)
    graph_file_exists = ("src/graph.py" in files) or ("src/graph.py".replace("\\", "/") in files)
    rubric_exists = ("rubric/week2_rubric.json" in files) or ("rubric/week2_rubric.json".replace("\\", "/") in files)

    commits = extract_git_history(repo_path)
    unsafe_os_system_files = scan_for_unsafe_os_system(repo_path)
    graph_facts = analyze_graph_structure(repo_path)

    evidences: Dict[str, List[Evidence]] = {}

    evidences.setdefault("forensic_accuracy_code", []).append(
        Evidence(
            goal="Git history progression exists",
            found=len(commits) > 0,
            content="\n".join([f"{c.ts} {c.sha[:8]} {c.msg}" for c in commits[:20]]) or None,
            location="git log --reverse",
            rationale="Collected using git log with timestamps",
            confidence=0.95,
        )
    )

    evidences["forensic_accuracy_code"].append(
        Evidence(
            goal="Typed state file exists",
            found=state_file_exists or graph_file_exists,
            content=f"src/state.py={state_file_exists}, src/graph.py={graph_file_exists}",
            location="repo file list",
            rationale="Checked repo tracked files",
            confidence=0.9,
        )
    )

    evidences["langgraph_architecture"] = [
        Evidence(
            goal="LangGraph StateGraph wiring shows fan-out/fan-in",
            found=bool(graph_facts.get("stategraph_used")),
            content=str(
                {
                    "stategraph_used": graph_facts.get("stategraph_used"),
                    "fan_out_detected": graph_facts.get("fan_out_detected"),
                    "fan_in_detected": graph_facts.get("fan_in_detected"),
                    "conditional_edges_detected": graph_facts.get("conditional_edges_detected"),
                    "fan_out_sources": graph_facts.get("fan_out_sources"),
                    "fan_in_targets": graph_facts.get("fan_in_targets"),
                }
            ),
            location="AST scan across repo",
            rationale="AST parsing of python files",
            confidence=0.75,
        )
    ]

    evidences["forensic_accuracy_code"].append(
        Evidence(
            goal="Safe tool engineering: avoids unsafe os.system",
            found=len(unsafe_os_system_files) == 0,
            content="\n".join(unsafe_os_system_files) or None,
            location="python file scan",
            rationale="Heuristic scan for os.system usage",
            confidence=0.7,
        )
    )

    evidences["forensic_accuracy_code"].append(
        Evidence(
            goal="Rubric file present in repo",
            found=rubric_exists,
            content="rubric/week2_rubric.json present" if rubric_exists else "missing",
            location="repo file list",
            rationale="Checked repo tracked files",
            confidence=0.9,
        )
    )

    return {
        "repo_local_path": repo_path,
        "workdir": workdir,
        "repo_commit_sha": commits[-1].sha if commits else "",
        "evidences": evidences,
    }


def doc_analyst(state: AgentState) -> Dict:
    pdf_path = state["pdf_path"]
    ing = ingest_pdf(pdf_path)

    chunks = ing["chunks"]
    paths = ing["paths_mentioned"]

    # Concept checks
    hits_dialectics = search_chunks(chunks, "Dialectical Synthesis")
    hits_metacog = search_chunks(chunks, "Metacognition")
    hits_fanin = search_chunks(chunks, "Fan-In")
    hits_fanout = search_chunks(chunks, "Fan-Out")

    evidences: Dict[str, List[Evidence]] = {}

    evidences["forensic_accuracy_docs"] = [
        Evidence(
            goal="PDF parsed and chunked",
            found=True,
            content=f"full_text_len={ing['full_text_len']}, chunks={len(chunks)}",
            location=pdf_path,
            rationale="Parsed using pypdf, chunked for RAG-lite",
            confidence=0.85,
        ),
        Evidence(
            goal="PDF contains theory explanations for dialectics/metacognition",
            found=bool(hits_dialectics or hits_metacog),
            content=_snip_hits(hits_dialectics, hits_metacog, hits_fanin, hits_fanout),
            location="PDF chunks",
            rationale="Keyword hits with surrounding chunk text",
            confidence=0.6,
        ),
        Evidence(
            goal="PDF cited file paths extracted",
            found=len(paths) > 0,
            content="\n".join(paths[:50]) or None,
            location="PDF text scan",
            rationale="Regex extraction of src/... paths",
            confidence=0.55,
        ),
    ]

    return {"evidences": evidences}


def _snip_hits(*hit_groups) -> str:
    out = []
    for hits in hit_groups:
        for idx, chunk in hits[:2]:
            out.append(f"[chunk {idx}] {chunk[:400].replace('\\n',' ')}")
    return "\n".join(out)[:2400]