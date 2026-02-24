from __future__ import annotations

import json
import os
from typing import Dict, List

from langchain_openai import ChatOpenAI

from src.state import AgentState, JudicialOpinion


def _rubric_map(rubric_dimensions: List[Dict]) -> Dict[str, Dict]:
    return {str(d.get("id")): d for d in (rubric_dimensions or []) if d.get("id")}


def _allowed_citations(state: AgentState, criterion_id: str) -> List[str]:
    evs = state["evidences"].get(criterion_id, [])
    out: List[str] = []
    for e in evs:
        loc = (e.location or "").strip()
        if loc:
            out.append(loc)
    # de-dup, keep order
    seen = set()
    uniq: List[str] = []
    for x in out:
        if x in seen:
            continue
        seen.add(x)
        uniq.append(x)
    return uniq[:12]


def _judge_llm() -> ChatOpenAI:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(model=model, temperature=0)


def _sanitize_citations(cited: List[str], allowed: List[str]) -> List[str]:
    if not allowed:
        return []
    allowed_set = set(allowed)
    kept = [c for c in (cited or []) if c in allowed_set]
    if kept:
        return kept[:12]
    return allowed[:12]


def _run_judge(state: AgentState, role: str, role_instructions: str) -> List[JudicialOpinion]:
    llm = _judge_llm().with_structured_output(JudicialOpinion, include_raw=False)

    outputs: List[JudicialOpinion] = []
    for dim in state["rubric_dimensions"]:
        cid = str(dim["id"])
        evidence = state["evidences"].get(cid, [])
        allowed = _allowed_citations(state, cid)

        forensic = str(dim.get("forensic_instruction", ""))
        success = str(dim.get("success_pattern", ""))
        failure = str(dim.get("failure_pattern", ""))

        prompt = (
            f"Role: {role}\n"
            f"{role_instructions}\n\n"
            "Hard rule:\n"
            "You must cite only from Allowed citations.\n"
            "If Allowed citations is empty, cited_evidence must be an empty list.\n"
            "You must not invent file paths, line numbers, tools, or commits.\n\n"
            "Return a JudicialOpinion object only.\n"
            "Score must be 1 to 5.\n\n"
            f"Criterion id: {cid}\n"
            f"Criterion name: {dim.get('name','')}\n\n"
            f"Forensic instruction:\n{forensic}\n\n"
            f"Success pattern:\n{success}\n\n"
            f"Failure pattern:\n{failure}\n\n"
            "Allowed citations:\n"
            f"{json.dumps(allowed, indent=2)}\n\n"
            "Evidence JSON:\n"
            f"{json.dumps([e.model_dump() for e in evidence], indent=2)}\n"
        )

        op: JudicialOpinion = llm.invoke(prompt)
        op.judge = role  # type: ignore[assignment]
        op.criterion_id = cid
        op.cited_evidence = _sanitize_citations(op.cited_evidence, allowed)
        outputs.append(op)

    return outputs


def prosecutor(state: AgentState) -> Dict:
    ops = _run_judge(
        state,
        role="Prosecutor",
        role_instructions="Be strict. Penalize missing artifacts and unsafe tooling.",
    )
    return {"opinions": ops}


def defense(state: AgentState) -> Dict:
    ops = _run_judge(
        state,
        role="Defense",
        role_instructions="Be generous, but stay factual. Reward partial compliance only when evidence supports it.",
    )
    return {"opinions": ops}


def tech_lead(state: AgentState) -> Dict:
    ops = _run_judge(
        state,
        role="TechLead",
        role_instructions="Be pragmatic. Focus on maintainability and correctness. Use evidence only.",
    )
    return {"opinions": ops}