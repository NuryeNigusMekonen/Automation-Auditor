## Goal
# Three judge nodes with structured output enforcement.

## Checklist
# Each judge returns JudicialOpinion
# Retry if parsing fails
# src/nodes/judges.py
from __future__ import annotations
import json
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from src.state import AgentState, JudicialOpinion

from langchain_openai import ChatOpenAI


class JudgeOut(BaseModel):
    score: int = Field(ge=1, le=5)
    reasoning: str
    citations: List[str] = Field(default_factory=list)


def _llm() -> ChatOpenAI:
    # Uses OPENAI_API_KEY from environment
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


def _judge_prompt(
    persona: Literal["Prosecutor", "Defense", "TechLead"],
    criterion: Dict,
    evidence_packet: str,
) -> str:
    cid = criterion.get("id", "")
    name = criterion.get("name", "")
    jl = (criterion.get("judicial_logic") or {}).get(persona.lower(), "")
    if isinstance(jl, list):
        jl_text = "\n".join([f"- {x}" for x in jl])
    else:
        jl_text = str(jl)

    return "\n".join(
        [
            "You are a judge in a Digital Courtroom. You must follow the rubric and cite evidence keys.",
            f"Persona: {persona}",
            f"Criterion: {cid} | {name}",
            "Rubric rules for this persona:",
            jl_text or "(no persona-specific rules provided)",
            "Evidence packet (facts only):",
            evidence_packet,
            "Output JSON with: score (1-5), reasoning, citations (list of evidence keys such as criterion id or ev indices).",
        ]
    )


def _run_judge(
    persona: Literal["Prosecutor", "Defense", "TechLead"],
    state: AgentState,
    criterion: Dict,
    evidence_packet: str,
    retry: int = 2,
) -> JudicialOpinion:
    llm = _llm().with_structured_output(JudgeOut)
    prompt = _judge_prompt(persona, criterion, evidence_packet)

    last_err: Optional[Exception] = None
    for _ in range(retry + 1):
        try:
            out: JudgeOut = llm.invoke(prompt)
            return JudicialOpinion(
                judge=persona,
                criterion_id=criterion.get("id", ""),
                score=out.score,
                argument=out.reasoning,
                cited_evidence=out.citations,
            )
        except Exception as e:
            last_err = e

    # Hard fallback if model output breaks
    return JudicialOpinion(
        judge=persona,
        criterion_id=criterion.get("id", ""),
        score=1,
        argument=f"Judge output parsing failed after retries: {type(last_err).__name__}",
        cited_evidence=[],
    )


def prosecutor_node(state: AgentState) -> Dict:
    return _judge_persona("Prosecutor", state)


def defense_node(state: AgentState) -> Dict:
    return _judge_persona("Defense", state)


def techlead_node(state: AgentState) -> Dict:
    return _judge_persona("TechLead", state)


def _judge_persona(persona: Literal["Prosecutor", "Defense", "TechLead"], state: AgentState) -> Dict:
    dims = state.get("rubric_dimensions", [])
    packets = state.get("evidence_packets", {})
    opinions: List[JudicialOpinion] = []

    for d in dims:
        cid = d.get("id", "")
        pkt = packets.get(cid, "No evidence packet.")
        opinions.append(_run_judge(persona, state, d, pkt))

    return {"opinions": opinions}