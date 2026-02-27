from __future__ import annotations

from typing import Dict, List, Set, Tuple

from src.state import AgentState, Evidence


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

    return uniq[:50]


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

    return sorted(uniq)[:2000]


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

    hit_locs = sorted(set(hit_locs))[:50]
    hit_snips = sorted(set(hit_snips))[:50]
    return hit_locs, hit_snips


def evidence_aggregator(state: AgentState) -> Dict:
    evidences = state.get("evidences", {}) or {}

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

    report_paths = _collect_report_paths(all_evs)
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
                    + verified_sorted[:200]
                    + [""]
                    + ["Hallucinated paths:"]
                    + hallucinated_sorted[:200]
                ),
                location="src/nodes/aggregator.py",
                rationale="Cross-referenced PDF paths against repository file index",
                confidence=0.9 if repo_files else 0.7,
            )
        )

        for p in verified_sorted[:200]:
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

        for p in hallucinated_sorted[:200]:
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
    has_hits = bool(hit_locs or hit_snips)

    security_signal = Evidence(
        goal="security_override_signal",
        found=has_hits,
        content=(
            "Unsafe execution detected:\n" + "\n".join(hit_snips[:25])
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

    citations = _flatten_locations(all_evs)
    citation_evidence = Evidence(
        goal="citation_pool",
        found=True,
        content="\n".join(citations),
        location="src/nodes/aggregator.py",
        rationale="Verified evidence locations for judge citation allowlist",
        confidence=0.9,
    )

    patch: Dict = {
        "evidences": {
            # Do not emit orchestration_guard here; the routing guard node owns it.
            "security_override_signal": [security_signal],
            "citation_pool": [citation_evidence],
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
