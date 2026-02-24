## Goal
# ChiefJusticeNode.

## Checklist
# Apply synthesis rules deterministically
# Generate markdown string
# src/nodes/justice.py
from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Tuple
from src.state import AgentState, JudicialOpinion, Evidence


def chief_justice(state: AgentState) -> Dict:
    dims = state.get("rubric_dimensions", [])
    evidences: Dict[str, List[Evidence]] = state.get("evidences", {})
    opinions: List[JudicialOpinion] = state.get("opinions", [])
    synth = _synthesis_rules_from_dimensions(state)

    by_crit: Dict[str, List[JudicialOpinion]] = defaultdict(list)
    for op in opinions:
        by_crit[op.criterion_id].append(op)

    verdicts: Dict[str, Dict] = {}
    for d in dims:
        cid = d.get("id", "")
        ops = by_crit.get(cid, [])
        evs = evidences.get(cid, [])
        verdicts[cid] = _resolve_one(cid, d, evs, ops, synth)

    md = _render_report(state, verdicts)
    return {"final_report": md}


def _synthesis_rules_from_dimensions(state: AgentState) -> Dict:
    # Rubric file already loaded; store synthesis_rules in state later if you want.
    # For now, keep defaults aligned with the shared constitution.
    return {
        "security_override_cap": 3,
        "variance_trigger": 2,
    }


def _resolve_one(cid: str, dim: Dict, evs: List[Evidence], ops: List[JudicialOpinion], synth: Dict) -> Dict:
    # Determine if a confirmed security flaw exists from evidence text
    security_flag = any(("os.system" in (e.content or "")) and (not e.found) for e in evs) or any(
        ("Security Negligence" in (op.argument or "")) for op in ops if op.judge == "Prosecutor"
    )

    scores = [op.score for op in ops] or [1]
    variance = max(scores) - min(scores) if scores else 0

    # Weighted preference: TechLead > Prosecutor > Defense for practicality
    tl = next((op for op in ops if op.judge == "TechLead"), None)
    pr = next((op for op in ops if op.judge == "Prosecutor"), None)
    df = next((op for op in ops if op.judge == "Defense"), None)

    base = tl.score if tl else (pr.score if pr else scores[0])

    # Variance rule: if high disagreement, bias toward TechLead, else median
    if variance > synth["variance_trigger"]:
        final = base
        reason = "High disagreement. Used TechLead-biased resolution."
    else:
        final = sorted(scores)[len(scores) // 2]
        reason = "Low disagreement. Used median of judge scores."

    # Security cap
    if security_flag:
        final = min(final, synth["security_override_cap"])
        reason += " Security override applied."

    dissent = _dissent_summary(pr, df, tl)

    remediation = _remediation_plan(cid, dim, evs, ops)

    return {
        "criterion_id": cid,
        "criterion_name": dim.get("name", ""),
        "final_score": int(final),
        "resolution_reason": reason,
        "dissent": dissent,
        "remediation": remediation,
        "opinions": [op.model_dump() for op in ops],
    }


def _dissent_summary(pr: JudicialOpinion | None, df: JudicialOpinion | None, tl: JudicialOpinion | None) -> str:
    parts = []
    if df and pr:
        parts.append(f"Defense={df.score} vs Prosecutor={pr.score}.")
    if tl:
        parts.append(f"TechLead={tl.score} used for practicality.")
    return " ".join(parts) if parts else "No dissent available."


def _remediation_plan(cid: str, dim: Dict, evs: List[Evidence], ops: List[JudicialOpinion]) -> List[str]:
    fixes: List[str] = []

    # Simple, file-level suggestions based on common failures
    if cid == "langgraph_architecture":
        if any(("fan_out_detected': False" in (e.content or "")) or ("fan_out_detected\": False" in (e.content or "")) for e in evs):
            fixes.append("Update src/graph.py to add fan-out branches for Detectives and Judges, and add a fan-in EvidenceAggregator node.")
        if any("conditional_edges_detected" in (e.content or "") and "False" in (e.content or "") for e in evs):
            fixes.append("Add conditional edges for missing evidence or node failures, for example retry DocAnalyst when PDF parse fails.")

    if cid == "forensic_accuracy_code":
        if any(e.goal == "Safe tool engineering: avoids unsafe os.system" and not e.found for e in evs):
            fixes.append("Replace os.system usage in tools with subprocess.run and validate inputs. Clone into tempfile.TemporaryDirectory().")
        fixes.append("Ensure src/state.py defines Evidence and JudicialOpinion as Pydantic models and AgentState uses reducers for parallel nodes.")

    if cid == "judicial_nuance":
        fixes.append("In src/nodes/judges.py, ensure Prosecutor, Defense, TechLead prompts differ and enforce with_structured_output for JSON.")
        fixes.append("Ensure each JudicialOpinion includes criterion_id and citations that map to evidence keys.")

    if cid == "forensic_accuracy_docs":
        fixes.append("In the PDF report, include concrete explanations of Dialectical Synthesis and show how evidence fan-in precedes judge fan-out.")
        fixes.append("List real file paths and ensure they match the repo, avoid citing non-existent files.")

    if not fixes:
        fixes.append("No specific remediation inferred. Add more targeted evidence checks and map them to rubric dimensions.")
    return fixes


def _render_report(state: AgentState, verdicts: Dict[str, Dict]) -> str:
    repo = state.get("repo_url", "")
    sha = state.get("repo_commit_sha", "")
    pdf = state.get("pdf_path", "")

    lines: List[str] = []
    lines.append("# Audit Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"- Repo: {repo}")
    lines.append(f"- Commit: {sha}")
    lines.append(f"- PDF: {pdf}")
    lines.append("")

    lines.append("## Criterion Breakdown")
    for cid, v in verdicts.items():
        lines.append("")
        lines.append(f"### {v['criterion_name']} ({cid})")
        lines.append(f"- Final score: {v['final_score']}")
        lines.append(f"- Resolution: {v['resolution_reason']}")
        lines.append(f"- Dissent: {v['dissent']}")
        lines.append("- Opinions:")
        for op in v["opinions"]:
            lines.append(f"  - {op['judge']}: score={op['score']} citations={op.get('cited_evidence', [])}")
        lines.append("- Remediation:")
        for step in v["remediation"]:
            lines.append(f"  - {step}")

    lines.append("")
    lines.append("## Remediation Plan")
    for cid, v in verdicts.items():
        lines.append(f"- {cid}:")
        for step in v["remediation"]:
            lines.append(f"  - {step}")

    lines.append("")
    return "\n".join(lines)