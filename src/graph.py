from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from src.state import AgentState, Evidence
from src.nodes.aggregator import evidence_aggregator, opinions_aggregator
from src.nodes.detectives import doc_analyst, repo_investigator, vision_inspector
from src.nodes.judges import defense, prosecutor, tech_lead
from src.nodes.justice import chief_justice
from src.nodes.routing import needs_more_evidence


def _verbose_logging_enabled(state: AgentState) -> bool:
    cfg = state.get("runtime_config") or {}
    if isinstance(cfg, dict):
        return bool(cfg.get("verbose_logging", False))
    return False


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log_file_path(state: AgentState) -> str | None:
    cfg = state.get("runtime_config") or {}
    if isinstance(cfg, dict):
        path = cfg.get("log_file_path")
        if isinstance(path, str) and path.strip():
            return path
    return None


def _emit_step_log(state: AgentState, message: str) -> None:
    line = f"[{_timestamp_utc()}] {message}"
    print(line)

    log_path = _log_file_path(state)
    if not log_path:
        return

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # Keep pipeline execution resilient even if logging fails.
        pass


def _count_evidence_items(evidences: Any) -> int:
    if not isinstance(evidences, dict):
        return 0
    total = 0
    for value in evidences.values():
        if isinstance(value, list):
            total += len(value)
    return total


def _trace_node(name: str, fn: Callable[[AgentState], dict]) -> Callable[[AgentState], dict]:
    def _wrapped(state: AgentState) -> dict:
        if _verbose_logging_enabled(state):
            _emit_step_log(state, f"[STEP] {name}: start")

        out = fn(state)

        if _verbose_logging_enabled(state):
            keys = ", ".join(sorted(out.keys())) if isinstance(out, dict) else ""
            evidence_count = _count_evidence_items(out.get("evidences", {})) if isinstance(out, dict) else 0
            opinion_count = len(out.get("opinions", [])) if isinstance(out, dict) and isinstance(out.get("opinions"), list) else 0

            details = []
            if evidence_count:
                details.append(f"evidences={evidence_count}")
            if opinion_count:
                details.append(f"opinions={opinion_count}")

            suffix = f" ({', '.join(details)})" if details else ""
            _emit_step_log(state, f"[STEP] {name}: done -> keys=[{keys}]{suffix}")

        return out

    return _wrapped


def judges_dispatch(state: AgentState) -> dict:
    return {}


def abort(state: AgentState) -> dict:
    msg = "Guard blocked judge fan-out. Proceeding to Chief Justice with remediation only."
    ev = Evidence(
        goal="orchestration_guard",
        found=False,
        content=msg,
        location="src/graph.py",
        rationale="Routing guard detected missing required evidence keys",
        confidence=0.95,
    )
    return {"evidences": {"orchestration_guard": [ev]}}


def _route_after_guard(state: AgentState) -> str:
    evs = (state.get("evidences", {}) or {}).get("orchestration_guard", []) or []
    failed = any(e.found is False for e in evs)
    return "abort" if failed else "judges_dispatch"


def _route_after_opinions(state: AgentState) -> str:
    # Always synthesize, even if opinions is empty.
    return "chief_justice"


def build_graph():
    g = StateGraph(AgentState)

    # Detectives (fan-out)
    g.add_node("repo_investigator", _trace_node("repo_investigator", repo_investigator))
    g.add_node("doc_analyst", _trace_node("doc_analyst", doc_analyst))
    g.add_node("vision_inspector", _trace_node("vision_inspector", vision_inspector))

    # Evidence fan-in
    g.add_node("evidence_aggregator", _trace_node("evidence_aggregator", evidence_aggregator))

    # Guard
    g.add_node("orchestration_guard", _trace_node("orchestration_guard", needs_more_evidence))
    g.add_node("abort", _trace_node("abort", abort))

    # Judges (fan-out)
    g.add_node("judges_dispatch", _trace_node("judges_dispatch", judges_dispatch))
    g.add_node("prosecutor", _trace_node("prosecutor", prosecutor))
    g.add_node("defense", _trace_node("defense", defense))
    g.add_node("tech_lead", _trace_node("tech_lead", tech_lead))

    # Opinions fan-in
    g.add_node("opinions_aggregator", _trace_node("opinions_aggregator", opinions_aggregator))

    # Synthesis
    g.add_node("chief_justice", _trace_node("chief_justice", chief_justice))

    # START to detectives in parallel
    g.add_edge(START, "repo_investigator")
    g.add_edge(START, "doc_analyst")
    g.add_edge(START, "vision_inspector")

    # Detectives to evidence aggregator
    g.add_edge("repo_investigator", "evidence_aggregator")
    g.add_edge("doc_analyst", "evidence_aggregator")
    g.add_edge("vision_inspector", "evidence_aggregator")

    # Guard runs after evidence aggregation
    g.add_edge("evidence_aggregator", "orchestration_guard")

    # Route after guard
    g.add_conditional_edges(
        "orchestration_guard",
        _route_after_guard,
        {
            "judges_dispatch": "judges_dispatch",
            "abort": "abort",
        },
    )

    # Abort still produces a report via synthesis
    g.add_edge("abort", "chief_justice")

    # Judge fan-out
    g.add_edge("judges_dispatch", "prosecutor")
    g.add_edge("judges_dispatch", "defense")
    g.add_edge("judges_dispatch", "tech_lead")

    # Judge fan-in
    g.add_edge("prosecutor", "opinions_aggregator")
    g.add_edge("defense", "opinions_aggregator")
    g.add_edge("tech_lead", "opinions_aggregator")

    # Always go to Chief Justice
    g.add_conditional_edges(
        "opinions_aggregator",
        _route_after_opinions,
        {
            "chief_justice": "chief_justice",
        },
    )

    g.add_edge("chief_justice", END)

    return g.compile()