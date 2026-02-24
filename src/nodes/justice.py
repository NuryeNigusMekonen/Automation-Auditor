import json
import os
from typing import Dict, List, Optional, Tuple

from src.state import AgentState, AuditReport, CriterionResult, Evidence, JudicialOpinion


def _score_variance(scores: List[int]) -> int:
    if not scores:
        return 0
    return max(scores) - min(scores)


def _detect_confirmed_security_flaw(evidences: Dict[str, List[Evidence]]) -> bool:
    evs = evidences.get("safe_tool_engineering", [])
    for ev in evs:
        if not ev.content:
            continue
        try:
            payload = json.loads(ev.content)
            if payload.get("os_system_detected") is True:
                return True
        except Exception:
            continue
    return False


def _dissent_summary(opinions: List[JudicialOpinion]) -> str:
    p = [o for o in opinions if o.judge == "Prosecutor"]
    d = [o for o in opinions if o.judge == "Defense"]
    t = [o for o in opinions if o.judge == "TechLead"]
    p_txt = p[0].argument if p else ""
    d_txt = d[0].argument if d else ""
    t_txt = t[0].argument if t else ""
    return (
        "Conflict detected.\n"
        f"Prosecutor: {p_txt}\n"
        f"Defense: {d_txt}\n"
        f"TechLead: {t_txt}\n"
    )


def _pick_final_score(
    dimension_id: str,
    evidences: Dict[str, List[Evidence]],
    opinions: List[JudicialOpinion],
) -> Tuple[int, Optional[str]]:
    scores = [o.score for o in opinions]
    variance = _score_variance(scores)

    # Rule of Security override
    security_flaw = _detect_confirmed_security_flaw(evidences)
    if security_flaw:
        # cap at 3, but do not force to 3 if all are below
        capped = min(3, max(scores)) if scores else 1
        dissent = _dissent_summary(opinions) if variance > 2 else None
        return capped, dissent

    # Rule of Evidence (fact supremacy)
    # If evidence for this dimension is missing/found False, cap score at 2
    dim_evs = evidences.get(dimension_id, [])
    if dim_evs and any(ev.found is False for ev in dim_evs):
        cap = min(2, max(scores)) if scores else 1
        dissent = _dissent_summary(opinions) if variance > 2 else None
        return cap, dissent

    # Variance re-evaluation rule
    if variance > 2:
        # Prefer TechLead as tie-breaker
        tech = next((o for o in opinions if o.judge == "TechLead"), None)
        final = tech.score if tech else sorted(scores)[1]
        return final, _dissent_summary(opinions)

    # Functionality weight for graph_orchestration
    if dimension_id == "graph_orchestration":
        tech = next((o for o in opinions if o.judge == "TechLead"), None)
        if tech:
            return tech.score, None

    # Default: median
    if not scores:
        return 1, None
    scores_sorted = sorted(scores)
    final = scores_sorted[len(scores_sorted) // 2]
    return final, None


def _remediation_for_dimension(dimension_id: str, evidences: Dict[str, List[Evidence]]) -> str:
    if dimension_id == "safe_tool_engineering":
        return (
            "Replace any os.system usage with subprocess.run([...], check=False, capture_output=True, text=True).\n"
            "Run git clone inside a sandboxed temporary directory.\n"
            "Add error handling: check return codes and include stderr in Evidence when failures occur.\n"
        )
    if dimension_id == "graph_orchestration":
        return (
            "Ensure two parallel fan-out and fan-in patterns exist.\n"
            "Detectives: START -> (repo_investigator, doc_analyst, vision_inspector) -> evidence_aggregator.\n"
            "Judges: evidence_aggregator -> (prosecutor, defense, techlead) -> chief_justice.\n"
            "Add at least one conditional edge for missing PDF or node failure handling.\n"
        )
    if dimension_id == "structured_output_enforcement":
        return (
            "Call LLM using with_structured_output(JudicialOpinion) or bind_tools bound to JudicialOpinion.\n"
            "Retry once on parse failure.\n"
            "Reject free text outputs.\n"
        )
    if dimension_id == "judicial_nuance":
        return (
            "Make Prosecutor, Defense, TechLead prompts materially different.\n"
            "Ensure each judge uses a distinct philosophy and produces different trade-off reasoning.\n"
            "Run judges in parallel branches in the graph.\n"
        )
    if dimension_id == "report_accuracy":
        return (
            "List all file paths referenced in the PDF.\n"
            "Cross-reference with repo file list.\n"
            "Remove or correct hallucinated file claims.\n"
        )
    if dimension_id == "theoretical_depth":
        return (
            "Explain Dialectical Synthesis with concrete mapping to your graph.\n"
            "Explain Fan-In/Fan-Out using specific node names and edges.\n"
            "Explain Metacognition as the evaluator judging evaluator quality.\n"
        )
    if dimension_id == "swarm_visual":
        return (
            "Add a diagram that shows two parallel sections.\n"
            "Detectives fan-out then fan-in.\n"
            "Judges fan-out then fan-in.\n"
            "Show Chief Justice synthesis to END.\n"
        )
    if dimension_id == "git_forensic_analysis":
        return (
            "Use more than 3 commits.\n"
            "Commit progression should reflect setup, tool engineering, graph wiring, judicial layer, synthesis.\n"
            "Avoid bulk upload patterns.\n"
        )
    if dimension_id == "state_management_rigor":
        return (
            "Use Pydantic BaseModel for Evidence and JudicialOpinion.\n"
            "Use TypedDict for AgentState.\n"
            "Use Annotated reducers operator.add and operator.ior to prevent parallel overwrites.\n"
        )
    if dimension_id == "chief_justice_synthesis":
        return (
            "Chief Justice must be deterministic Python logic.\n"
            "Implement security override, fact supremacy, and dissent requirement.\n"
            "Write final Markdown report to file.\n"
        )
    return "Add file-level fixes that match the rubric success pattern for this criterion.\n"


def _render_markdown(report: AuditReport) -> str:
    lines: List[str] = []
    lines.append("# Audit Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(report.executive_summary.strip())
    lines.append("")
    lines.append(f"Overall Score: {report.overall_score:.2f}")
    lines.append("")
    lines.append("## Criterion Breakdown")
    lines.append("")
    for c in report.criteria:
        lines.append(f"### {c.dimension_name} ({c.dimension_id})")
        lines.append("")
        lines.append(f"Final Score: {c.final_score}")
        lines.append("")
        if c.dissent_summary:
            lines.append("Dissent Summary:")
            lines.append(c.dissent_summary.strip())
            lines.append("")
        lines.append("Judge Opinions:")
        for o in c.judge_opinions:
            lines.append(f"- {o.judge} Score {o.score}: {o.argument.strip()}")
            if o.cited_evidence:
                lines.append(f"  Cited evidence: {', '.join(o.cited_evidence)}")
        lines.append("")
        lines.append("Remediation:")
        lines.append(c.remediation.strip())
        lines.append("")
    lines.append("## Remediation Plan")
    lines.append("")
    lines.append(report.remediation_plan.strip())
    lines.append("")
    return "\n".join(lines)


def chief_justice(state: AgentState) -> AgentState:
    dims = state.get("rubric_dimensions", [])
    evidences = state.get("evidences", {})
    opinions_all = state.get("opinions", [])

    criteria: List[CriterionResult] = []

    for dim in dims:
        did = dim["id"]
        dname = dim["name"]
        opinions = [o for o in opinions_all if o.criterion_id == did]
        final_score, dissent = _pick_final_score(did, evidences, opinions)
        remediation = _remediation_for_dimension(did, evidences)

        criteria.append(
            CriterionResult(
                dimension_id=did,
                dimension_name=dname,
                final_score=final_score,
                judge_opinions=opinions,
                dissent_summary=dissent if _score_variance([o.score for o in opinions]) > 2 else None,
                remediation=remediation,
            )
        )

    if criteria:
        overall = sum(c.final_score for c in criteria) / float(len(criteria))
    else:
        overall = 1.0

    executive = (
        "This audit report was generated by a Digital Courtroom agent.\n"
        "Detectives produced forensic evidence. Judges scored each criterion independently.\n"
        "Chief Justice applied deterministic synthesis rules to produce final scores and remediation steps."
    )

    remediation_plan = "Prioritize safety and orchestration first. Then improve structured outputs and documentation accuracy.\n"

    report = AuditReport(
        repo_url=state["repo_url"],
        executive_summary=executive,
        overall_score=overall,
        criteria=criteria,
        remediation_plan=remediation_plan,
    )

    state["final_report"] = report

    md = _render_markdown(report)

    out_path = state.get("out_path") or ""
    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)

    return state