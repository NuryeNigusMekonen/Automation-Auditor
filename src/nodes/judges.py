from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Set, Tuple

from langchain_openai import ChatOpenAI

from src.state import AgentState, Evidence, JudicialOpinion


def _env_int(name: str, default: int, *, min_value: int = 1, max_value: int = 10000) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(min_value, min(value, max_value))


CAP_ALLOWED_CITATIONS = _env_int("AUDITOR_CAP_ALLOWED_CITATIONS", 50, max_value=2000)
CAP_CITED_EVIDENCE = _env_int("AUDITOR_CAP_CITED_EVIDENCE", 12, max_value=200)
CAP_EVIDENCE_ITEMS = _env_int("AUDITOR_CAP_EVIDENCE_ITEMS", 80, max_value=5000)


def _runtime_cap(state: AgentState, key: str, default: int) -> int:
    cfg = state.get("runtime_config") or {}
    if isinstance(cfg, dict):
        value = cfg.get(key)
        if isinstance(value, int) and value > 0:
            return value
    return default


def _is_affirmative_security_claim(argument: str) -> bool:
    arg_low = (argument or "").lower()
    if not arg_low:
        return False

    negated_patterns = (
        "no confirmed security flaw",
        "no confirmed security flaws",
        "no confirmed security vulnerability",
        "no confirmed security vulnerabilities",
        "no evidence of confirmed security flaw",
        "no evidence of confirmed security flaws",
        "no evidence of confirmed security vulnerability",
        "no evidence of confirmed security vulnerabilities",
        "without confirmed security flaw",
        "without confirmed security flaws",
        "without confirmed security vulnerability",
        "without confirmed security vulnerabilities",
        "not a confirmed security flaw",
        "not a confirmed security vulnerability",
    )

    if any(p in arg_low for p in negated_patterns):
        return False

    if re.search(
        r"\b(no|not|without)\b[^\n\r\.]{0,80}\bconfirmed security (flaw|flaws|vulnerability|vulnerabilities)\b",
        arg_low,
    ):
        return False

    if re.search(
        r"\bno evidence of\b[^\n\r\.]{0,80}\b(a\s+)?confirmed security (flaw|flaws|vulnerability|vulnerabilities)\b",
        arg_low,
    ):
        return False

    if re.search(
        r"\babsence of evidence (for|of)\b[^\n\r\.]{0,80}\b(a\s+)?confirmed security (flaw|flaws|vulnerability|vulnerabilities)\b",
        arg_low,
    ):
        return False

    if re.search(
        r"\babsence of\b[^\n\r\.]{0,40}\b(any\s+)?confirmed security (flaw|flaws|vulnerability|vulnerabilities)\b",
        arg_low,
    ):
        return False

    if (
        "security_override_signal=false" in arg_low
        or "security_override_signal is false" in arg_low
    ):
        return False

    if re.search(
        r"\bconfirmed security (flaw|flaws|vulnerability|vulnerabilities)\b",
        arg_low,
    ):
        return True

    if "security_override_signal" in arg_low and "false" not in arg_low:
        return True

    return False


def _judge_llm() -> ChatOpenAI:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(model=model, temperature=0)


def _merge_evidence_for_criterion(
    state: AgentState, criterion_id: str
) -> List[Evidence]:
    evidences = state.get("evidences", {}) or {}
    out: List[Evidence] = []

    out.extend(list(evidences.get(criterion_id, []) or []))

    # Global signals that judges must respect.
    out.extend(list(evidences.get("security_override_signal", []) or []))
    out.extend(list(evidences.get("orchestration_guard", []) or []))

    # For report accuracy scoring, include the crossref summary if present.
    if criterion_id == "report_accuracy":
        out.extend(list(evidences.get("repo_file_index", []) or []))

    return out


def _collect_allowed(
    state: AgentState, criterion_id: str, evidence: List[Evidence]
) -> List[str]:
    allowed: List[str] = []

    for e in evidence or []:
        loc = (e.location or "").strip()
        if loc:
            allowed.append(loc)

    pool_evs = (state.get("evidences", {}) or {}).get("citation_pool", []) or []
    for e in pool_evs:
        if not e.content:
            continue
        for line in e.content.splitlines():
            s = line.strip()
            if s:
                allowed.append(s)

    seen: Set[str] = set()
    uniq: List[str] = []
    for x in allowed:
        if x in seen:
            continue
        seen.add(x)
        uniq.append(x)

    return uniq[:CAP_ALLOWED_CITATIONS]


def _sanitize_citations(cited: List[str], allowed: List[str]) -> List[str]:
    if not allowed:
        return []
    allowed_set = set(allowed)
    kept = [c for c in (cited or []) if c in allowed_set]
    return kept[:CAP_CITED_EVIDENCE]


def _normalize_citations_for_criterion(
    criterion_id: str,
    cited: List[str],
    allowed: List[str],
) -> List[str]:
    if not cited:
        return []

    preferred_prefixes: Dict[str, Tuple[str, ...]] = {
        "structured_output_enforcement": ("src/nodes/judges.py",),
        "judicial_nuance": ("src/nodes/judges.py",),
        "chief_justice_synthesis": ("src/nodes/justice.py",),
        "graph_orchestration": ("src/graph.py",),
        "state_management_rigor": ("src/state.py",),
        "safe_tool_engineering": ("src/tools",),
    }

    prefixes = preferred_prefixes.get(criterion_id)
    if not prefixes:
        return cited[:CAP_CITED_EVIDENCE]

    narrowed = [c for c in cited if c.startswith(prefixes)]
    if narrowed:
        return narrowed[:CAP_CITED_EVIDENCE]

    fallback = [a for a in allowed if a.startswith(prefixes)]
    if fallback:
        return fallback[:1]

    return cited[:CAP_CITED_EVIDENCE]


def _offline_judicial_opinion(
    role: str,
    criterion_id: str,
    evidence: List[Evidence],
    allowed: List[str],
) -> JudicialOpinion:
    has_evidence = bool(evidence)
    any_negative = any(e.found is False for e in (evidence or []))

    if not has_evidence:
        score = 1
    elif any_negative:
        score = 2
    else:
        score = 4

    role_word = {
        "Prosecutor": "risk",
        "Defense": "effort",
        "TechLead": "maintainability",
    }.get(role, "analysis")

    summary = (
        f"{role_word}: offline deterministic evaluation for {criterion_id}. "
        f"evidence_items={len(evidence)} any_negative={any_negative}."
    )

    return JudicialOpinion(
        judge=role,
        criterion_id=criterion_id,
        score=score,
        argument=summary,
        cited_evidence=allowed[:1],
    )


def _has_confirmed_security_signal(evidence: List[Evidence]) -> bool:
    for e in evidence or []:
        if e.goal == "security_override_signal" and e.found is True:
            return True
        if e.goal == "safe_tool_engineering" and e.found is False:
            return True
        if (e.content or "").find("Unsafe execution call sites detected:") >= 0:
            return True
    return False


def _structured_output_telemetry(
    role: str,
    criterion_id: str,
    retries: int,
    fallback_used: bool,
    last_err: str,
    offline_mode: bool,
) -> Evidence:
    status = "offline" if offline_mode else ("fallback" if fallback_used else "ok")
    parts = [
        f"judge={role}",
        f"criterion_id={criterion_id}",
        f"status={status}",
        f"retries={retries}",
        f"fallback_used={str(fallback_used).lower()}",
    ]
    if last_err:
        parts.append(f"last_error={last_err}")

    return Evidence(
        goal="structured_output_enforcement",
        found=not fallback_used,
        content="; ".join(parts),
        location="src/nodes/judges.py",
        rationale="Judge structured-output runtime telemetry for retry/fallback handling",
        confidence=0.95 if not fallback_used else 0.85,
    )


def _run_judge(
    state: AgentState,
    role: str,
    philosophy: str,
    behavioral_contract: str,
) -> Tuple[List[JudicialOpinion], List[Evidence]]:
    offline_mode = bool(state.get("offline_mode", False))
    outputs: List[JudicialOpinion] = []
    telemetry: List[Evidence] = []

    for dim in state["rubric_dimensions"]:
        cid = str(dim.get("id", ""))
        if not cid:
            continue

        evidence = _merge_evidence_for_criterion(state, cid)
        allowed = _collect_allowed(state, cid, evidence)

        forensic = str(dim.get("forensic_instruction", ""))
        success = str(dim.get("success_pattern", ""))
        failure = str(dim.get("failure_pattern", ""))

        security_confirmed = _has_confirmed_security_signal(evidence)

        op: JudicialOpinion
        last_err = ""
        retries = 0
        fallback_used = False

        if offline_mode:
            op = _offline_judicial_opinion(role, cid, evidence, allowed)
        else:
            llm = _judge_llm().with_structured_output(JudicialOpinion, include_raw=False)
            cap_evidence_items = _runtime_cap(
                state,
                "cap_evidence_items",
                CAP_EVIDENCE_ITEMS,
            )

            prompt = (
                f"You are acting as: {role}\n\n"
                f"Philosophy:\n{philosophy}\n\n"
                f"Behavioral contract:\n{behavioral_contract}\n\n"
                "Mandatory constraints:\n"
                "- Score is integer 1 to 5.\n"
                "- Cite only from Allowed citations.\n"
                "- If Allowed citations is empty, cited_evidence is [].\n"
                "- Never invent file paths or tools.\n"
                "- Return only a JudicialOpinion object.\n"
                "- You must not claim a security flaw is confirmed unless security_confirmed=true.\n"
                "- If security_confirmed=false, you may say no confirmed security flaw in evidence.\n\n"
                f"security_confirmed={str(security_confirmed).lower()}\n\n"
                f"Criterion id: {cid}\n"
                f"Criterion name: {dim.get('name', '')}\n\n"
                f"Forensic instruction:\n{forensic}\n\n"
                f"Success pattern:\n{success}\n\n"
                f"Failure pattern:\n{failure}\n\n"
                "Allowed citations:\n"
                f"{json.dumps(allowed, indent=2)}\n\n"
                "Evidence JSON:\n"
                f"{json.dumps([e.model_dump() for e in evidence[:cap_evidence_items]], indent=2)}\n"
            )

            for attempt in range(3):
                try:
                    op = llm.invoke(prompt)
                    break
                except Exception as e:
                    last_err = f"{type(e).__name__}: {e}"
                    retries = attempt + 1
                    if attempt < 2:
                        prompt = (
                            prompt
                            + "\n\nRetry rule: Return a valid JudicialOpinion object that matches the schema exactly."
                        )
                        continue

                    op = JudicialOpinion(
                        judge=role,
                        criterion_id=cid,
                        score=1,
                        argument=f"risk: structured output failure. detail={last_err}",
                        cited_evidence=[],
                    )
                    fallback_used = True

        op.judge = role
        op.criterion_id = cid
        op.cited_evidence = _sanitize_citations(op.cited_evidence, allowed)
        op.cited_evidence = _normalize_citations_for_criterion(
            cid,
            op.cited_evidence,
            allowed,
        )

        if allowed and not op.cited_evidence:
            pick = allowed[0]

            if cid == "report_accuracy":
                for a in allowed:
                    if a.startswith(("src/", "rubric/", "audit/", "reports/")):
                        pick = a
                        break

            if cid == "safe_tool_engineering":
                for a in allowed:
                    if a == "src/tools" or a.startswith("src/tools/"):
                        pick = a
                        break

            op.cited_evidence = [pick]
            op.argument = op.argument + f" Added deterministic citation: {pick}."

        # If the judge still cites nothing, cap score.
        if allowed and not op.cited_evidence:
            op.score = min(op.score, 2)
            op.argument = (
                op.argument + " Evidence missing in citations. Score capped to 2."
            )

        # Enforce the security-confirmed rule at output time too.
        # Only penalize affirmative claims, not denials like
        # "no evidence of confirmed security flaws".
        affirmative = _is_affirmative_security_claim(op.argument or "")

        if affirmative and not security_confirmed:
            op.score = min(int(op.score), 2)
            op.argument = (
                op.argument + " Security claim not supported by evidence. Score capped."
            )

        outputs.append(op)
        telemetry.append(
            _structured_output_telemetry(
                role=role,
                criterion_id=cid,
                retries=retries,
                fallback_used=fallback_used,
                last_err=last_err,
                offline_mode=offline_mode,
            )
        )

    return outputs, telemetry


def prosecutor(state: AgentState) -> Dict:
    opinions, telemetry = _run_judge(
        state,
        role="Prosecutor",
        philosophy="Assume non-compliance unless proven. Search for risk, vulnerability, architectural weakness, and missing artifacts.",
        behavioral_contract="Your argument contains the word risk. Penalize ambiguity. If deterministic logic is not visible in evidence, treat it as absent.",
    )
    return {
        "opinions": opinions,
        "evidences": {"structured_output_enforcement": telemetry},
    }


def defense(state: AgentState) -> Dict:
    opinions, telemetry = _run_judge(
        state,
        role="Defense",
        philosophy="Assume good intent. Reward effort when supported by evidence. Partial compliance gets proportional credit.",
        behavioral_contract="Your argument contains the word effort. Acknowledge incremental improvement. Interpret evidence in the developer favor when reasonable.",
    )
    return {
        "opinions": opinions,
        "evidences": {"structured_output_enforcement": telemetry},
    }


def tech_lead(state: AgentState) -> Dict:
    opinions, telemetry = _run_judge(
        state,
        role="TechLead",
        philosophy="Evaluate production readiness. Focus on maintainability, correctness, and operational safety.",
        behavioral_contract="Your argument contains the word maintainability. Ignore academic language without implementation proof. If confirmed security flaw exists, keep score at 3 or lower.",
    )
    return {
        "opinions": opinions,
        "evidences": {"structured_output_enforcement": telemetry},
    }
