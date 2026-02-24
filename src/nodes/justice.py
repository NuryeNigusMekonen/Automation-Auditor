from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from src.state import Evidence, JudicialOpinion


@dataclass
class CriterionVerdict:
    criterion_id: str
    criterion_name: str
    final_score: int
    dissent_summary: str
    remediation: str
    opinions: List[JudicialOpinion]


def _rubric_index(rubric_dimensions: List[Dict]) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for d in rubric_dimensions or []:
        did = str(d.get("id", "")).strip()
        if did:
            out[did] = d
    return out


def _group_opinions(opinions: List[JudicialOpinion]) -> Dict[str, List[JudicialOpinion]]:
    grouped: Dict[str, List[JudicialOpinion]] = {}
    for op in opinions or []:
        grouped.setdefault(op.criterion_id, []).append(op)
    return grouped


def _scores_by_judge(ops: List[JudicialOpinion]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for op in ops:
        out[str(op.judge)] = int(op.score)
    return out


def _variance(scores: List[int]) -> int:
    if not scores:
        return 0
    return max(scores) - min(scores)


def _pick_final_score(scores: Dict[str, int]) -> int:
    if "TechLead" in scores:
        return int(scores["TechLead"])
    if "Prosecutor" in scores and "Defense" in scores:
        return int(round((scores["Prosecutor"] + scores["Defense"]) / 2))
    if scores:
        return int(list(scores.values())[0])
    return 1


def _security_flag(text: str) -> bool:
    t = (text or "").lower()
    needles = ["os.system", "shell injection", "unsanitized", "no sanitization", "raw os.system"]
    return any(n in t for n in needles)


def _evidence_missing(evs: List[Evidence]) -> bool:
    if not evs:
        return False
    return any(e.found is False for e in evs)


def _render_markdown(
    repo_url: str,
    overall_score: float,
    verdicts: List[CriterionVerdict],
    remediation_plan: str,
) -> str:
    lines: List[str] = []
    lines.append("# Audit Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"Repo: {repo_url}")
    lines.append(f"Overall score: {overall_score:.2f} / 5.00")
    lines.append("")
    lines.append("## Criterion Breakdown")

    for v in verdicts:
        lines.append("")
        lines.append(f"### {v.criterion_name} ({v.criterion_id})")
        lines.append(f"Final score: {v.final_score} / 5")

        if v.dissent_summary:
            lines.append("Dissent:")
            lines.append(v.dissent_summary)

        lines.append("Judge opinions:")
        for op in v.opinions:
            lines.append(f"- {op.judge}: {op.score}/5")
            lines.append(f"  Argument: {op.argument}")
            if op.cited_evidence:
                lines.append(f"  Cited evidence: {', '.join(op.cited_evidence)}")

        lines.append("Remediation:")
        lines.append(v.remediation)

    lines.append("")
    lines.append("## Remediation Plan")
    lines.append(remediation_plan or "No remediation plan generated.")
    lines.append("")
    return "\n".join(lines)


def chief_justice(state: Dict) -> Dict:
    repo_url: str = state.get("repo_url", "")
    rubric_dimensions: List[Dict] = state.get("rubric_dimensions", []) or []
    evidences: Dict[str, List[Evidence]] = state.get("evidences", {}) or {}
    opinions: List[JudicialOpinion] = state.get("opinions", []) or []

    rubric = _rubric_index(rubric_dimensions)
    grouped = _group_opinions(opinions)

    verdicts: List[CriterionVerdict] = []
    per_scores: List[int] = []

    security_issue_found = False

    for crit_id, ops in grouped.items():
        dim = rubric.get(crit_id, {})
        crit_name = str(dim.get("name") or crit_id)

        scores_map = _scores_by_judge(ops)
        raw_scores = list(scores_map.values())
        var = _variance(raw_scores)

        final_score = _pick_final_score(scores_map)

        evs = evidences.get(crit_id, []) or []
        if _evidence_missing(evs):
            final_score = min(final_score, 2)

        prosecutor_op = next((o for o in ops if o.judge == "Prosecutor"), None)
        if prosecutor_op and _security_flag(prosecutor_op.argument):
            security_issue_found = True

        dissent = ""
        if var > 2:
            p = scores_map.get("Prosecutor")
            d = scores_map.get("Defense")
            t = scores_map.get("TechLead")
            dissent = f"Variance {var}. Prosecutor={p}, Defense={d}, TechLead={t}. Final score follows TechLead priority, then evidence rules."

        remediation = str(dim.get("failure_pattern") or dim.get("forensic_instruction") or "Add missing evidence and rerun.")
        verdicts.append(
            CriterionVerdict(
                criterion_id=crit_id,
                criterion_name=crit_name,
                final_score=int(final_score),
                dissent_summary=dissent,
                remediation=remediation,
                opinions=ops,
            )
        )
        per_scores.append(int(final_score))

    overall = (sum(per_scores) / len(per_scores)) if per_scores else 1.0
    if security_issue_found:
        overall = min(overall, 3.0)

    low: List[Tuple[str, int]] = sorted(
        [(v.criterion_id, v.final_score) for v in verdicts],
        key=lambda x: x[1],
    )
    remediation_lines: List[str] = []
    remediation_lines.append("Fix lowest scores first.")
    for cid, sc in low[:5]:
        dim = rubric.get(cid, {})
        name = str(dim.get("name") or cid)
        fp = str(dim.get("failure_pattern") or "").strip()
        remediation_lines.append(f"- {name} ({cid}) score={sc}. {fp}")

    md = _render_markdown(
        repo_url=repo_url,
        overall_score=overall,
        verdicts=verdicts,
        remediation_plan="\n".join(remediation_lines),
    )

    return {"final_report_markdown": md, "final_report": {"overall_score": overall}}