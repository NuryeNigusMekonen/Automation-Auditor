# src/nodes/justice.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from src.state import Evidence, JudicialOpinion


@dataclass
class CriterionVerdict:
    criterion_id: str
    criterion_name: str
    final_score: int
    dissent_summary: str
    remediation: str
    opinions: List[JudicialOpinion]


def _group_opinions(
    opinions: List[JudicialOpinion],
) -> Dict[str, List[JudicialOpinion]]:
    grouped: Dict[str, List[JudicialOpinion]] = {}
    for op in opinions or []:
        grouped.setdefault(str(op.criterion_id), []).append(op)
    return grouped


def _scores_by_judge(ops: List[JudicialOpinion]) -> Dict[str, int]:
    allowed = {"Prosecutor", "Defense", "TechLead"}
    out: Dict[str, int] = {}
    for op in ops:
        j = str(op.judge)
        if j not in allowed:
            continue
        try:
            sc = int(op.score)
        except Exception:
            sc = 1
        if sc < 1:
            sc = 1
        if sc > 5:
            sc = 5
        out[j] = sc
    return out


def _variance(scores: List[int]) -> int:
    return (max(scores) - min(scores)) if scores else 0


def _evidence_missing(evs: List[Evidence]) -> bool:
    return any(e.found is False for e in (evs or []))


def _security_signal_true(evidences: Dict[str, List[Evidence]]) -> bool:
    evs = evidences.get("security_override_signal", []) or []
    return any(e.found is True for e in evs)


def _pick_final_score(scores: Dict[str, int], criterion_id: str) -> int:
    # Rubric synthesis_rules.functionality_weight
    if criterion_id == "graph_orchestration" and "TechLead" in scores:
        return scores["TechLead"]

    # Default priority: TechLead > Prosecutor > Defense
    if "TechLead" in scores:
        return scores["TechLead"]
    if "Prosecutor" in scores:
        return scores["Prosecutor"]
    if "Defense" in scores:
        return scores["Defense"]
    return 1


def _apply_fact_supremacy(
    final_score: int,
    scores: Dict[str, int],
    evs: List[Evidence],
) -> tuple[int, str]:
    if not _evidence_missing(evs):
        return final_score, ""

    updated = min(int(final_score), 2)
    defense_score = scores.get("Defense")
    if defense_score is not None and defense_score >= 4:
        return (
            updated,
            "Fact supremacy applied: defense optimism was overruled by negative/missing evidence.",
        )

    return (
        updated,
        "Fact supremacy applied: negative/missing evidence capped criterion score.",
    )


def _re_evaluate_high_variance(
    final_score: int,
    scores: Dict[str, int],
    evs: List[Evidence],
    criterion_id: str,
) -> tuple[int, str]:
    updated = int(final_score)

    if _evidence_missing(evs):
        updated = min(updated, 2)
        return (
            updated,
            "Variance re-evaluation: conflicting opinions resolved conservatively due to negative/missing evidence.",
        )

    if criterion_id == "graph_orchestration" and "TechLead" in scores:
        updated = int(scores["TechLead"])
        return (
            updated,
            "Variance re-evaluation: graph orchestration follows TechLead functionality weighting.",
        )

    if scores:
        avg = round(sum(scores.values()) / len(scores))
        updated = max(1, min(5, int(avg)))
        return (
            updated,
            "Variance re-evaluation: used rounded inter-judge mean after tie-break review.",
        )

    return updated, "Variance re-evaluation: insufficient judge scores; kept baseline score."


def _get_judge_score(ops: List[JudicialOpinion], judge: str) -> Optional[int]:
    for op in ops or []:
        if str(op.judge) == judge:
            try:
                return int(op.score)
            except Exception:
                return None
    return None


def _render_markdown(
    repo_url: str,
    overall_score: float,
    verdicts: List[CriterionVerdict],
    remediation_plan: str,
    executive_details: str,
) -> str:
    lines: List[str] = []
    lines.append("# Audit Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"Repo: {repo_url}")
    lines.append(f"Overall score: {overall_score:.2f} / 5.00")
    if executive_details:
        lines.append(executive_details)
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
        if not v.opinions:
            lines.append("- None")

        for op in v.opinions:
            lines.append(f"- {op.judge}: {op.score}/5")
            lines.append(f"  Argument: {op.argument}")
            if op.cited_evidence:
                lines.append("  Cited evidence: " + ", ".join(op.cited_evidence))

        lines.append("Remediation:")
        lines.append(v.remediation)

    lines.append("")
    lines.append("## Remediation Plan")
    lines.append(remediation_plan)
    lines.append("")
    return "\n".join(lines)


def chief_justice(state: Dict) -> Dict:
    """
    Deterministic synthesis with rubric-aligned rules.

    Rule of Security (rubric):
    - Only cap overall at 3.0 when:
      1) security_override_signal is true, AND
      2) Prosecutor score for safe_tool_engineering indicates a confirmed vuln (score <= 3).

    Rule of Evidence:
    - If any Evidence for a criterion has found=False, cap that criterion score at 2.

    Functionality weight:
    - For graph_orchestration, TechLead carries highest weight.

    Dissent requirement:
    - If variance across judge scores > 2, include dissent summary.

    Output:
    - Structured Markdown report.
    """
    repo_url = state.get("repo_url", "")
    rubric_dimensions = state.get("rubric_dimensions", []) or []
    evidences: Dict[str, List[Evidence]] = state.get("evidences", {}) or {}
    opinions: List[JudicialOpinion] = state.get("opinions", []) or []

    grouped = _group_opinions(opinions)

    verdicts: List[CriterionVerdict] = []
    per_scores: List[int] = []

    for dim in rubric_dimensions:
        cid = str(dim.get("id", ""))
        if not cid:
            continue

        name = str(dim.get("name") or cid)
        ops = grouped.get(cid, [])
        scores_map = _scores_by_judge(ops)
        raw_scores = list(scores_map.values())
        var = _variance(raw_scores)

        final_score = _pick_final_score(scores_map, cid)
        evs = evidences.get(cid, []) or []

        fact_note = ""
        final_score, fact_note = _apply_fact_supremacy(final_score, scores_map, evs)

        dissent = ""
        if var > 2:
            final_score, reeval_note = _re_evaluate_high_variance(
                final_score,
                scores_map,
                evs,
                cid,
            )
            dissent = (
                f"Variance {var}. "
                f"Prosecutor={scores_map.get('Prosecutor')}, "
                f"Defense={scores_map.get('Defense')}, "
                f"TechLead={scores_map.get('TechLead')}. "
                f"{reeval_note}"
            )
            if fact_note:
                dissent = dissent + " " + fact_note
        elif fact_note:
            dissent = fact_note

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

    # Rubric-aligned security cap: requires both signal and Prosecutor confirmation.
    security_signal = _security_signal_true(evidences)
    prosecutor_safe_score = _get_judge_score(
        grouped.get("safe_tool_engineering", []), "Prosecutor"
    )
    prosecutor_confirms = (
        prosecutor_safe_score is not None and prosecutor_safe_score <= 3
    )

    if security_signal and prosecutor_confirms:
        overall = min(overall, 3.0)

    lowest = sorted(
        [(v.criterion_name, v.final_score) for v in verdicts], key=lambda x: x[1]
    )
    highest = sorted(
        [(v.criterion_name, v.final_score) for v in verdicts], key=lambda x: x[1], reverse=True
    )

    dissent_count = sum(1 for v in verdicts if bool(v.dissent_summary))
    low_count = sum(1 for _, score in lowest if score <= 3)

    executive_lines: List[str] = []
    executive_lines.append(f"Criteria evaluated: {len(verdicts)}")
    executive_lines.append(f"Dissent-triggered criteria: {dissent_count}")
    executive_lines.append(
        f"Security override applied: {'yes' if (security_signal and prosecutor_confirms) else 'no'}"
    )

    executive_lines.append("Top strengths:")
    for name, score in highest[:3]:
        executive_lines.append(f"- {name}: {score}/5")

    executive_lines.append("Highest-risk criteria:")
    if low_count == 0:
        executive_lines.append("- None (all criteria above 3/5)")
    else:
        for name, score in lowest[:3]:
            if score <= 3:
                executive_lines.append(f"- {name}: {score}/5")

    remediation_lines: List[str] = ["Fix lowest scores first."]
    for verdict in sorted(verdicts, key=lambda v: v.final_score)[:5]:
        remediation_lines.append(f"- {verdict.criterion_name} score={verdict.final_score}")
        remediation_lines.append(f"  Action: {verdict.remediation}")

    md = _render_markdown(
        repo_url,
        overall,
        verdicts,
        "\n".join(remediation_lines),
        "\n".join(executive_lines),
    )

    return {
        "final_report_markdown": md,
        "final_report": {"overall_score": overall},
    }
