from __future__ import annotations

import json
import os
from typing import Dict, List

from langchain_openai import ChatOpenAI

from src.state import AgentState, JudicialOpinion


def _allowed_citations(state: AgentState, criterion_id: str) -> List[str]:
    evs = state["evidences"].get(criterion_id, [])
    out: List[str] = []
    for e in evs:
        loc = (e.location or "").strip()
        if loc:
            out.append(loc)

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
    return kept[:12]


def _run_judge(
    state: AgentState,
    role: str,
    philosophy: str,
    behavioral_contract: str,
) -> List[JudicialOpinion]:

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
            f"You are acting as: {role}\n\n"
            f"Philosophy:\n{philosophy}\n\n"
            f"Behavioral contract:\n{behavioral_contract}\n\n"
            "Mandatory constraints:\n"
            "- Score must be integer 1 to 5.\n"
            "- You must cite ONLY from Allowed citations.\n"
            "- If Allowed citations is empty, cited_evidence must be [].\n"
            "- Never invent file paths or tools.\n"
            "- Return ONLY a JudicialOpinion object.\n\n"
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
        op.judge = role
        op.criterion_id = cid
        op.cited_evidence = _sanitize_citations(op.cited_evidence, allowed)
        outputs.append(op)

    return outputs


def prosecutor(state: AgentState) -> Dict:
    return {
        "opinions": _run_judge(
            state,
            role="Prosecutor",
            philosophy=(
                "Assume non-compliance unless explicitly proven. "
                "Search for risk, vulnerability, architectural weakness, and missing artifacts."
            ),
            behavioral_contract=(
                "Your argument must contain the word 'risk'. "
                "Penalize ambiguity. "
                "If deterministic logic is not visible in evidence, treat it as absent."
            ),
        )
    }


def defense(state: AgentState) -> Dict:
    return {
        "opinions": _run_judge(
            state,
            role="Defense",
            philosophy=(
                "Assume good intent. Reward architectural effort when supported by evidence. "
                "Partial compliance deserves proportional credit."
            ),
            behavioral_contract=(
                "Your argument must contain the word 'effort'. "
                "Acknowledge incremental improvement. "
                "Interpret evidence in the developer’s favor when reasonable."
            ),
        )
    }


def tech_lead(state: AgentState) -> Dict:
    return {
        "opinions": _run_judge(
            state,
            role="TechLead",
            philosophy=(
                "Evaluate production readiness. Focus on maintainability, correctness, and operational safety."
            ),
            behavioral_contract=(
                "Your argument must contain the word 'maintainability'. "
                "Ignore academic language without implementation proof. "
                "If a confirmed security flaw exists, cap score at 3."
            ),
        )
    }