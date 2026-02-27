from __future__ import annotations

import os
from typing import Dict, List, Set, Tuple

from src.state import AgentState, Evidence


def _env_int(name: str, default: int, *, min_value: int = 1, max_value: int = 20000) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(min_value, min(value, max_value))


CAP_LOCATIONS = _env_int("AUDITOR_CAP_LOCATIONS", 50, max_value=2000)
CAP_REPORT_PATHS = _env_int("AUDITOR_CAP_REPORT_PATHS", 2000, max_value=50000)
CAP_CROSSREF_PER_TYPE = _env_int("AUDITOR_CAP_CROSSREF_PER_TYPE", 200, max_value=5000)
CAP_SECURITY_LOCATIONS = _env_int("AUDITOR_CAP_SECURITY_LOCATIONS", 50, max_value=2000)
CAP_SECURITY_SNIPPETS = _env_int("AUDITOR_CAP_SECURITY_SNIPPETS", 50, max_value=2000)
CAP_SECURITY_SIGNAL_SNIPPETS = _env_int("AUDITOR_CAP_SECURITY_SIGNAL_SNIPPETS", 25, max_value=500)


def _runtime_cap(state: AgentState, key: str, default: int) -> int:
    cfg = state.get("runtime_config") or {}
    if isinstance(cfg, dict):
        value = cfg.get(key)
        if isinstance(value, int) and value > 0:
            return value
    return default


def _flatten_locations(evs: List[Evidence]) -> List[str]:
    out: List[str] = []
    for e in evs or []:
        if getattr(e, "found", False) is not True:
            continue
        loc = (e.location or "").strip()
        if loc:
            out.append(loc)

    seen: Set[str] = set()
    uniq: List[str] = []
    for x in out:
        if x in seen:
            continue
        seen.add(x)
        uniq.append(x)

    return uniq[:CAP_LOCATIONS]


def _collect_report_paths(all_evs: List[Evidence]) -> List[str]:
    paths: List[str] = []
    for e in all_evs:
        if e.goal != "report_accuracy":
            continue
        if not e.content:
            continue
        for line in e.content.splitlines():
            p = line.strip()
            if p.startswith(("src/", "rubric/", "audit/", "reports/")):
                paths.append(p)

    seen: Set[str] = set()
    uniq: List[str] = []
    for p in paths:
        if p in seen:
            continue
        seen.add(p)
        uniq.append(p)

    return sorted(uniq)[:CAP_REPORT_PATHS]


def _collect_security_hit_locations(evs: List[Evidence]) -> Tuple[List[str], List[str]]:
    hit_locs: List[str] = []
    hit_snips: List[str] = []

    for e in evs or []:
        txt = e.content or ""
        if not txt:
            continue

        if "Unsafe execution call sites detected:" in txt:
            loc = (e.location or "").strip()
            if loc:
                hit_locs.append(loc)

            take = False
            for line in txt.splitlines():
                s = line.strip()
                if not s:
                    continue
                if s.startswith("Unsafe execution call sites detected:"):
                    take = True
                    continue
                if s.startswith("Safe signals detected:"):
                    take = False
                    continue
                if take:
                    hit_snips.append(s)

        if (
            "Unsafe usage detected:" in txt
            or "os.system(" in txt
            or "shell=True" in txt
        ):
            loc = (e.location or "").strip()
            if loc:
                hit_locs.append(loc)

    hit_locs = sorted(set(hit_locs))[:CAP_SECURITY_LOCATIONS]
    hit_snips = sorted(set(hit_snips))[:CAP_SECURITY_SNIPPETS]
    return hit_locs, hit_snips


def _build_cross_detective_consistency(
    evidences: Dict[str, List[Evidence]],
) -> Evidence:
    git_evs = evidences.get("git_forensic_analysis", []) or []
    graph_evs = evidences.get("graph_orchestration", []) or []
    report_acc_evs = evidences.get("report_accuracy", []) or []

    git_positive = any(e.found is True for e in git_evs)
    graph_positive = any(e.found is True for e in graph_evs)
    report_has_hallucinations = any(e.found is False for e in report_acc_evs)

    lines = [
        f"git_positive={str(git_positive).lower()}",
        f"graph_positive={str(graph_positive).lower()}",
        f"report_hallucinations={str(report_has_hallucinations).lower()}",
    ]

    if git_positive and graph_positive:
        lines.append("link: git evolution evidence aligns with graph orchestration evidence")
    if report_has_hallucinations:
        lines.append("link: report claims include unverifiable or missing paths")

    return Evidence(
        goal="cross_detective_consistency",
        found=not report_has_hallucinations,
        content="\n".join(lines),
        location="src/nodes/aggregator.py",
        rationale="Cross-links repository forensics, graph structure findings, and report-accuracy signals",
        confidence=0.85 if report_has_hallucinations else 0.9,
    )


def evidence_aggregator(state: AgentState) -> Dict:
    evidences = state.get("evidences", {}) or {}
    cap_locations = _runtime_cap(state, "cap_locations", CAP_LOCATIONS)
    cap_report_paths = _runtime_cap(state, "cap_report_paths", CAP_REPORT_PATHS)
    cap_crossref_per_type = _runtime_cap(
        state,
        "cap_crossref_per_type",
        CAP_CROSSREF_PER_TYPE,
    )
    cap_security_locations = _runtime_cap(
        state,
        "cap_security_locations",
        CAP_SECURITY_LOCATIONS,
    )
    cap_security_snippets = _runtime_cap(
        state,
        "cap_security_snippets",
        CAP_SECURITY_SNIPPETS,
    )
    cap_security_signal_snippets = _runtime_cap(
        state,
        "cap_security_signal_snippets",
        CAP_SECURITY_SIGNAL_SNIPPETS,
    )

    all_evs: List[Evidence] = []
    for _, evs in evidences.items():
        all_evs.extend(list(evs or []))

    repo_files: Set[str] = set()
    repo_index_evs = evidences.get("repo_file_index", []) or []
    for e in repo_index_evs:
        if not e.content:
            continue
        for line in e.content.splitlines():
            p = line.strip()
            if p:
                repo_files.add(p)

    report_paths = _collect_report_paths(all_evs)[:cap_report_paths]
    verified: List[str] = []
    hallucinated: List[str] = []
    if repo_files and report_paths:
        for p in report_paths:
            if p in repo_files:
                verified.append(p)
            else:
                hallucinated.append(p)

    crossref_evs: List[Evidence] = []
    if report_paths:
        verified_sorted = sorted(verified)
        hallucinated_sorted = sorted(hallucinated)

        crossref_evs.append(
            Evidence(
                goal="report_accuracy",
                found=True,
                content="\n".join(
                    ["Verified paths:"]
                    + verified_sorted[:cap_crossref_per_type]
                    + [""]
                    + ["Hallucinated paths:"]
                    + hallucinated_sorted[:cap_crossref_per_type]
                ),
                location="src/nodes/aggregator.py",
                rationale="Cross-referenced PDF paths against repository file index",
                confidence=0.9 if repo_files else 0.7,
            )
        )

        for p in verified_sorted[:cap_crossref_per_type]:
            crossref_evs.append(
                Evidence(
                    goal="report_accuracy",
                    found=True,
                    content=None,
                    location=p,
                    rationale="Mentioned in PDF and present in repository index",
                    confidence=0.9,
                )
            )

        for p in hallucinated_sorted[:cap_crossref_per_type]:
            crossref_evs.append(
                Evidence(
                    goal="report_accuracy",
                    found=False,
                    content=None,
                    location=p,
                    rationale="Mentioned in PDF but missing from repository index",
                    confidence=0.9,
                )
            )

    safe_evs = evidences.get("safe_tool_engineering", []) or []
    hit_locs, hit_snips = _collect_security_hit_locations(safe_evs)
    hit_locs = hit_locs[:cap_security_locations]
    hit_snips = hit_snips[:cap_security_snippets]
    has_hits = bool(hit_locs or hit_snips)

    security_signal = Evidence(
        goal="security_override_signal",
        found=has_hits,
        content=(
            "Unsafe execution detected:\n" + "\n".join(hit_snips[:cap_security_signal_snippets])
            if hit_snips
            else (
                "Unsafe execution detected."
                if has_hits
                else "No confirmed unsafe execution surfaces"
            )
        ),
        location="src/tools",
        rationale="Derived from safe_tool_engineering evidence scanner output",
        confidence=0.95,
    )

    citations = _flatten_locations(all_evs)[:cap_locations]
    citation_evidence = Evidence(
        goal="citation_pool",
        found=True,
        content="\n".join(citations),
        location="src/nodes/aggregator.py",
        rationale="Verified evidence locations for judge citation allowlist",
        confidence=0.9,
    )
    cross_detective_consistency = _build_cross_detective_consistency(evidences)

    patch: Dict = {
        "evidences": {
            # Do not emit orchestration_guard here; the routing guard node owns it.
            "security_override_signal": [security_signal],
            "citation_pool": [citation_evidence],
            "cross_detective_consistency": [cross_detective_consistency],
        }
    }
    if crossref_evs:
        patch["evidences"]["report_accuracy"] = crossref_evs

    return patch


def opinions_aggregator(state: AgentState) -> Dict:
    ops = state.get("opinions", []) or []
    counts: Dict[str, int] = {}
    for op in ops:
        cid = str(op.criterion_id)
        counts[cid] = counts.get(cid, 0) + 1

    ev = Evidence(
        goal="opinions_summary",
        found=True,
        content="\n".join([f"{k} opinions={v}" for k, v in sorted(counts.items())]),
        location="src/nodes/aggregator.py",
        rationale="Summarized judge outputs per criterion",
        confidence=0.9,
    )
    return {"evidences": {"opinions_summary": [ev]}}
