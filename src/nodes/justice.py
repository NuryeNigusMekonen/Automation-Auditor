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
    return {str(d.get("id")): d for d in rubric_dimensions or [] if d.get("id")}


def _group_opinions(opinions: List[JudicialOpinion]) -> Dict[str, List[JudicialOpinion]]:
    grouped: Dict[str, List[JudicialOpinion]] = {}
    for op in opinions or []:
        grouped.setdefault(op.criterion_id, []).append(op)
    return grouped


def _scores_by_judge(ops: List[JudicialOpinion]) -> Dict[str, int]:
    return {str(op.judge): int(op.score) for op in ops}


def _variance(scores: List[int]) -> int:
    return max(scores) - min(scores) if scores else 0


def _security_flag(text: str) -> bool:
    t = (text or "").lower()
    needles = ["os.system", "shell injection", "unsanitized", "raw os.system"]
    return any(n in t for n in needles)


def _evidence_missing(evs: List[Evidence]) -> bool:
    return any(e.found is False for e in (evs or []))


def _pick_final_score(scores: Dict[str, int]) -> int:
    if "TechLead" in scores:
        return scores["TechLead"]
    if "Prosecutor" in scores:
        return scores["Prosecutor"]
    if "Defense" in scores:
        return scores["Defense"]
    return 1


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
    lines.append(remediation_plan)
    lines.append("")
    return "\n".join(lines)


def chief_justice(state: Dict) -> Dict:

    repo_url = state.get("repo_url", "")
    rubric_dimensions = state.get("rubric_dimensions", []) or []
    evidences = state.get("evidences", {}) or {}
    opinions = state.get("opinions", []) or []

    rubric = _rubric_index(rubric_dimensions)
    grouped = _group_opinions(opinions)

    verdicts: List[CriterionVerdict] = []
    per_scores: List[int] = []

    security_issue = False

    for cid, ops in grouped.items():

        dim = rubric.get(cid, {})
        name = str(dim.get("name") or cid)

        scores_map = _scores_by_judge(ops)
        raw_scores = list(scores_map.values())
        var = _variance(raw_scores)

        final_score = _pick_final_score(scores_map)

        evs = evidences.get(cid, [])
        if _evidence_missing(evs):
            final_score = min(final_score, 2)

        prosecutor_op = next((o for o in ops if o.judge == "Prosecutor"), None)
        if prosecutor_op and _security_flag(prosecutor_op.argument):
            security_issue = True

        dissent = ""
        if var > 2:
            dissent = (
                f"Variance {var}. "
                f"Prosecutor={scores_map.get('Prosecutor')}, "
                f"Defense={scores_map.get('Defense')}, "
                f"TechLead={scores_map.get('TechLead')}. "
                "Final score follows priority rules."
            )

        remediation = str(
            dim.get("failure_pattern")
            or dim.get("forensic_instruction")
            or "Add missing implementation evidence."
        )

        verdicts.append(
            CriterionVerdict(
                criterion_id=cid,
                criterion_name=name,
                final_score=int(final_score),
                dissent_summary=dissent,
                remediation=remediation,
                opinions=ops,
            )
        )

        per_scores.append(int(final_score))

    overall = (sum(per_scores) / len(per_scores)) if per_scores else 1.0

    if security_issue:
        overall = min(overall, 3.0)

    lowest = sorted(
        [(v.criterion_name, v.final_score) for v in verdicts],
        key=lambda x: x[1],
    )

    remediation_lines = ["Fix lowest scores first."]
    for name, score in lowest[:5]:
        remediation_lines.append(f"- {name} score={score}")

    md = _render_markdown(repo_url, overall, verdicts, "\n".join(remediation_lines))

    return {"final_report_markdown": md, "final_report": {"overall_score": overall}}