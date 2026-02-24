import json
from typing import Dict, List

from langchain_openai import ChatOpenAI

from src.state import AgentState, JudicialOpinion


def _persona_system_prompt(judge: str) -> str:
    if judge == "Prosecutor":
        return (
            "You are the Prosecutor Judge.\n"
            "Trust no one. Assume shortcuts.\n"
            "If evidence suggests linear orchestration, missing typed state, missing structured output, or unsafe tooling, score low.\n"
            "You must cite evidence keys in cited_evidence.\n"
            "Return only structured output."
        )
    if judge == "Defense":
        return (
            "You are the Defense Judge.\n"
            "Reward effort and intent.\n"
            "If evidence shows deep thought, iteration, or partial compliance, give partial credit.\n"
            "You must cite evidence keys in cited_evidence.\n"
            "Return only structured output."
        )
    return (
        "You are the TechLead Judge.\n"
        "Be pragmatic. Does it work and is it maintainable.\n"
        "Tie-break between Prosecutor and Defense.\n"
        "Weight architectural correctness and safety highest.\n"
        "You must cite evidence keys in cited_evidence.\n"
        "Return only structured output."
    )


def _judge_one(llm: ChatOpenAI, judge: str, dim: Dict, evidence_packet: str) -> JudicialOpinion:
    sys = _persona_system_prompt(judge)
    user = {
        "task": "Score this criterion from 1 to 5 and provide a precise argument and cited evidence keys.",
        "criterion_id": dim["id"],
        "criterion_name": dim["name"],
        "forensic_instruction": dim.get("forensic_instruction", ""),
        "success_pattern": dim.get("success_pattern", ""),
        "failure_pattern": dim.get("failure_pattern", ""),
        "evidence_packet_json": json.loads(evidence_packet) if evidence_packet else {},
        "output_rules": {
            "score_range": "1..5",
            "argument": "Must reference evidence facts and rubric patterns",
            "cited_evidence": "List of criterion ids you used, e.g. ['graph_orchestration']",
        },
    }

    model = llm.with_structured_output(JudicialOpinion)
    # retry if structured parsing fails
    last_err = None
    for _ in range(2):
        try:
            out = model.invoke(
                [
                    {"role": "system", "content": sys},
                    {"role": "user", "content": json.dumps(user, indent=2)},
                ]
            )
            # fill required fields if missing
            out.judge = judge  # type: ignore
            out.criterion_id = dim["id"]  # type: ignore
            if not out.cited_evidence:
                out.cited_evidence = [dim["id"]]  # type: ignore
            return out
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Judge {judge} failed to produce structured output for {dim['id']}: {last_err}")


def prosecutor_node(state: AgentState) -> AgentState:
    llm = ChatOpenAI(model=state.get("model", "gpt-4o-mini"), temperature=0)
    packets = state.get("evidence_packets", {})
    dims = state.get("rubric_dimensions", [])
    opinions: List[JudicialOpinion] = []

    for dim in dims:
        pid = dim["id"]
        evidence_packet = packets.get(pid, "")
        opinions.append(_judge_one(llm, "Prosecutor", dim, evidence_packet))

    state["opinions"] = opinions
    return state


def defense_node(state: AgentState) -> AgentState:
    llm = ChatOpenAI(model=state.get("model", "gpt-4o-mini"), temperature=0)
    packets = state.get("evidence_packets", {})
    dims = state.get("rubric_dimensions", [])
    opinions: List[JudicialOpinion] = []

    for dim in dims:
        pid = dim["id"]
        evidence_packet = packets.get(pid, "")
        opinions.append(_judge_one(llm, "Defense", dim, evidence_packet))

    state["opinions"] = opinions
    return state


def techlead_node(state: AgentState) -> AgentState:
    llm = ChatOpenAI(model=state.get("model", "gpt-4o-mini"), temperature=0)
    packets = state.get("evidence_packets", {})
    dims = state.get("rubric_dimensions", [])
    opinions: List[JudicialOpinion] = []

    for dim in dims:
        pid = dim["id"]
        evidence_packet = packets.get(pid, "")
        opinions.append(_judge_one(llm, "TechLead", dim, evidence_packet))

    state["opinions"] = opinions
    return state