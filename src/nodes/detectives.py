import json
import os
from typing import Dict, List

from src.state import AgentState, Evidence
from src.tools.ast_tools import analyze_graph_structure, find_pydantic_and_reducers
from src.tools.git_tools import clone_repo, get_git_log, get_head_commit, list_repo_files, scan_for_os_system
from src.tools.pdf_tools import cross_reference_paths, ingest_pdf
from src.tools.vision_tools import extract_images_from_pdf


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def repo_investigator(state: AgentState) -> AgentState:
    workdir, repo_path = clone_repo(state["repo_url"])
    head = get_head_commit(repo_path)
    repo_files = list_repo_files(repo_path)
    os_system_detected = scan_for_os_system(repo_path)

    # Git forensic analysis
    commits = get_git_log(repo_path)
    commit_payload = {
        "total_commits": len(commits),
        "commits": [{"sha": c.sha, "ts": c.ts, "msg": c.msg} for c in commits],
        "bulk_upload_risk": (len(commits) <= 2),
    }

    # State management rigor (inspect target repo files if present)
    # This node evaluates the TARGET repo, not our own repo.
    # We still try to locate src/state.py in target.
    state_flags: Dict[str, bool] = {}
    state_snippet = ""
    for candidate in ["src/state.py", "src/graph.py"]:
        if candidate in repo_files:
            txt = _read_file(os.path.join(repo_path, candidate))
            if candidate.endswith("state.py"):
                state_flags = find_pydantic_and_reducers(txt)
                state_snippet = "\n".join(txt.splitlines()[:120])
            else:
                # graph.py may contain TypedDict/BaseModel too, attempt scan
                state_flags = find_pydantic_and_reducers(txt)
                state_snippet = "\n".join(txt.splitlines()[:120])
            break

    # Graph orchestration (inspect src/graph.py if present)
    graph_payload = {}
    graph_snippet = ""
    for candidate in ["src/graph.py", "graph.py"]:
        if candidate in repo_files:
            txt = _read_file(os.path.join(repo_path, candidate))
            gs = analyze_graph_structure(txt)
            graph_payload = {
                "stategraph_used": gs.stategraph_used,
                "add_edge_calls": gs.add_edge_calls,
                "add_conditional_edges_calls": gs.add_conditional_edges_calls,
                "start_fanout_edges": gs.start_fanout_edges,
                "has_aggregator_node": gs.has_aggregator_node,
                "notes": gs.notes,
            }
            graph_snippet = "\n".join(txt.splitlines()[:160])
            break

    # Safe tool engineering evidence (signals only)
    tool_payload = {
        "os_system_detected": os_system_detected,
        "notes": "os.system is a security risk. Prefer subprocess.run with args list and error handling.",
    }

    # Structured output enforcement and judicial nuance and chief justice
    # These are best-effort: we look for expected files and key strings.
    judges_payload = {"has_judges_file": ("src/nodes/judges.py" in repo_files)}
    justice_payload = {"has_justice_file": ("src/nodes/justice.py" in repo_files)}

    evidences: Dict[str, List[Evidence]] = {}

    evidences["git_forensic_analysis"] = [
        Evidence(
            goal="Extract commit history and detect iterative progression",
            found=True,
            content=json.dumps(commit_payload, indent=2),
            location=head,
            rationale="git log extracted from cloned repository",
            confidence=0.9,
        )
    ]

    evidences["state_management_rigor"] = [
        Evidence(
            goal="Verify typed state, Pydantic models, and reducers",
            found=bool(state_flags),
            content=json.dumps({"flags": state_flags, "snippet_head": state_snippet}, indent=2),
            location="src/state.py or src/graph.py",
            rationale="AST scan for BaseModel, TypedDict, Annotated, operator.add, operator.ior",
            confidence=0.75 if state_flags else 0.4,
        )
    ]

    evidences["graph_orchestration"] = [
        Evidence(
            goal="Verify parallel fan-out/fan-in architecture and conditional edges",
            found=bool(graph_payload),
            content=json.dumps({"analysis": graph_payload, "snippet_head": graph_snippet}, indent=2),
            location="src/graph.py",
            rationale="AST scan for StateGraph usage and add_edge/add_conditional_edges calls",
            confidence=0.75 if graph_payload else 0.4,
        )
    ]

    evidences["safe_tool_engineering"] = [
        Evidence(
            goal="Detect unsafe shell usage and lack of sandboxing",
            found=True,
            content=json.dumps(tool_payload, indent=2),
            location="repo scan",
            rationale="Scanned repo for 'os.system(' occurrences as a security signal",
            confidence=0.6,
        )
    ]

    evidences["structured_output_enforcement"] = [
        Evidence(
            goal="Check for structured output enforcement in judge nodes",
            found=judges_payload["has_judges_file"],
            content=json.dumps(judges_payload, indent=2),
            location="src/nodes/judges.py",
            rationale="File existence check as baseline, detailed enforcement is judged by judges node output",
            confidence=0.5,
        )
    ]

    evidences["judicial_nuance"] = [
        Evidence(
            goal="Check persona separation exists in judge prompts",
            found=judges_payload["has_judges_file"],
            content=json.dumps({"note": "Persona nuance requires distinct prompts and parallel judge execution."}, indent=2),
            location="src/nodes/judges.py",
            rationale="Presence indicates possible role separation, full verification requires deeper prompt diff logic",
            confidence=0.45,
        )
    ]

    evidences["chief_justice_synthesis"] = [
        Evidence(
            goal="Check Chief Justice deterministic rules and markdown report output",
            found=justice_payload["has_justice_file"],
            content=json.dumps({"note": "Chief Justice should be deterministic rules, not an LLM average."}, indent=2),
            location="src/nodes/justice.py",
            rationale="File presence check, full verification done by judges and synthesis rules",
            confidence=0.45,
        )
    ]

    state["workdir"] = workdir
    state["repo_local_path"] = repo_path
    state["repo_commit_sha"] = head
    state["evidences"] = evidences
    return state


def doc_analyst(state: AgentState) -> AgentState:
    pdf_path = state.get("pdf_path") or ""
    repo_path = state.get("repo_local_path") or ""
    evidences: Dict[str, List[Evidence]] = {}

    if not pdf_path or not os.path.exists(pdf_path):
        evidences["theoretical_depth"] = [
            Evidence(
                goal="Parse PDF for theoretical depth terms",
                found=False,
                content=None,
                location=pdf_path or "<missing>",
                rationale="PDF path not provided or file not found",
                confidence=0.9,
            )
        ]
        evidences["report_accuracy"] = [
            Evidence(
                goal="Cross-reference report file paths against repo files",
                found=False,
                content=None,
                location=pdf_path or "<missing>",
                rationale="PDF missing, cannot extract paths",
                confidence=0.9,
            )
        ]
        state["evidences"] = evidences
        return state

    pdf = ingest_pdf(pdf_path)

    # Theoretical depth
    depth_payload = {
        "text_len": len(pdf.full_text),
        "chunk_count": len(pdf.chunks),
        "keyword_hits": {k: v[:5] for k, v in pdf.keyword_hits.items()},
    }

    # Report accuracy cross-reference
    repo_files = []
    if repo_path and os.path.exists(repo_path):
        for root, _, files in os.walk(repo_path):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), repo_path)
                repo_files.append(rel)
        repo_files.sort()

    verified, hallucinated = cross_reference_paths(pdf.mentioned_paths, repo_files)
    accuracy_payload = {
        "mentioned_paths": pdf.mentioned_paths,
        "verified_paths": verified,
        "hallucinated_paths": hallucinated,
        "verified_count": len(verified),
        "hallucinated_count": len(hallucinated),
    }

    evidences["theoretical_depth"] = [
        Evidence(
            goal="Check for substantive explanation of Dialectical Synthesis, Fan-In/Fan-Out, Metacognition, State Synchronization",
            found=True,
            content=json.dumps(depth_payload, indent=2),
            location=pdf_path,
            rationale="PDF parsed and keyword snippets extracted",
            confidence=0.7,
        )
    ]

    evidences["report_accuracy"] = [
        Evidence(
            goal="Cross-reference file paths claimed in report against actual repo",
            found=True,
            content=json.dumps(accuracy_payload, indent=2),
            location=pdf_path,
            rationale="Extracted file paths from report and compared to repo file list",
            confidence=0.7,
        )
    ]

    state["evidences"] = evidences
    return state


def vision_inspector(state: AgentState) -> AgentState:
    pdf_path = state.get("pdf_path") or ""
    evidences: Dict[str, List[Evidence]] = {}

    if not state.get("enable_vision", False):
        evidences["swarm_visual"] = [
            Evidence(
                goal="Extract and analyze architectural diagrams",
                found=False,
                content=json.dumps({"reason": "vision disabled by flag"}, indent=2),
                location=pdf_path or "<missing>",
                rationale="Vision execution is optional, implementation required",
                confidence=0.9,
            )
        ]
        state["evidences"] = evidences
        return state

    if not pdf_path or not os.path.exists(pdf_path):
        evidences["swarm_visual"] = [
            Evidence(
                goal="Extract and analyze architectural diagrams",
                found=False,
                content=json.dumps({"reason": "pdf missing"}, indent=2),
                location=pdf_path or "<missing>",
                rationale="No PDF to extract images from",
                confidence=0.9,
            )
        ]
        state["evidences"] = evidences
        return state

    images = extract_images_from_pdf(pdf_path)
    payload = {
        "image_count": len(images),
        "images": [{"page_index": i.page_index, "name": i.name} for i in images[:25]],
        "note": "Execution optional. If you enable vision, extend this node to send images to a vision model.",
    }

    evidences["swarm_visual"] = [
        Evidence(
            goal="Extract images and classify diagram type and parallelism",
            found=True,
            content=json.dumps(payload, indent=2),
            location=pdf_path,
            rationale="PDF image extraction attempted using pypdf",
            confidence=0.55,
        )
    ]

    state["evidences"] = evidences
    return state