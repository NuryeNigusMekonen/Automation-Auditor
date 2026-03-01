from src.nodes.judges import prosecutor
from src.state import Evidence, JudicialOpinion


class _RetryThenSuccessLLM:
    def __init__(self) -> None:
        self.calls = 0

    def with_structured_output(self, *_args, **_kwargs):
        return self

    def invoke(self, _prompt: str) -> JudicialOpinion:
        self.calls += 1
        if self.calls == 1:
            raise ValueError("malformed output")
        return JudicialOpinion(
            judge="Prosecutor",
            criterion_id="safe_tool_engineering",
            score=4,
            argument="risk",
            cited_evidence=["src/tools"],
        )


class _AlwaysFailLLM:
    def with_structured_output(self, *_args, **_kwargs):
        return self

    def invoke(self, _prompt: str) -> JudicialOpinion:
        raise ValueError("still malformed")


class _NoConfirmedFlawsLLM:
    def with_structured_output(self, *_args, **_kwargs):
        return self

    def invoke(self, _prompt: str) -> JudicialOpinion:
        return JudicialOpinion(
            judge="Prosecutor",
            criterion_id="safe_tool_engineering",
            score=5,
            argument=(
                "There is no evidence of a confirmed security flaw. "
                "This implementation aligns with best practices."
            ),
            cited_evidence=["src/tools"],
        )


class _AbsenceOfEvidenceLLM:
    def with_structured_output(self, *_args, **_kwargs):
        return self

    def invoke(self, _prompt: str) -> JudicialOpinion:
        return JudicialOpinion(
            judge="Prosecutor",
            criterion_id="safe_tool_engineering",
            score=5,
            argument=(
                "The absence of evidence for a confirmed security flaw is in the "
                "developer's favor."
            ),
            cited_evidence=["src/tools"],
        )


class _AbsenceOfAnyConfirmedFlawLLM:
    def with_structured_output(self, *_args, **_kwargs):
        return self

    def invoke(self, _prompt: str) -> JudicialOpinion:
        return JudicialOpinion(
            judge="Prosecutor",
            criterion_id="safe_tool_engineering",
            score=5,
            argument="The absence of any confirmed security flaw is noted.",
            cited_evidence=["src/tools"],
        )


def _state() -> dict:
    return {
        "offline_mode": False,
        "rubric_dimensions": [
            {
                "id": "safe_tool_engineering",
                "name": "Safe Tool Engineering",
                "forensic_instruction": "inspect",
                "success_pattern": "safe",
                "failure_pattern": "unsafe",
            }
        ],
        "evidences": {
            "safe_tool_engineering": [
                Evidence(
                    goal="safe_tool_engineering",
                    found=True,
                    content="ok",
                    location="src/tools",
                    rationale="scan",
                    confidence=0.9,
                )
            ],
            "citation_pool": [
                Evidence(
                    goal="citation_pool",
                    found=True,
                    content="src/tools",
                    location="src/nodes/aggregator.py",
                    rationale="pool",
                    confidence=0.9,
                )
            ],
        },
    }


def test_retry_telemetry_records_success_after_retry(monkeypatch) -> None:
    monkeypatch.setattr("src.nodes.judges._judge_llm", lambda: _RetryThenSuccessLLM())

    out = prosecutor(_state())
    telemetry = out["evidences"]["structured_output_enforcement"][0]

    assert telemetry.goal == "structured_output_enforcement"
    assert telemetry.found is True
    assert "status=ok" in (telemetry.content or "")
    assert "retries=1" in (telemetry.content or "")
    assert "fallback_used=false" in (telemetry.content or "")


def test_retry_telemetry_records_fallback_after_max_retries(monkeypatch) -> None:
    monkeypatch.setattr("src.nodes.judges._judge_llm", lambda: _AlwaysFailLLM())

    out = prosecutor(_state())
    telemetry = out["evidences"]["structured_output_enforcement"][0]
    opinion = out["opinions"][0]

    assert telemetry.goal == "structured_output_enforcement"
    assert telemetry.found is False
    assert "status=fallback" in (telemetry.content or "")
    assert "retries=3" in (telemetry.content or "")
    assert "fallback_used=true" in (telemetry.content or "")
    assert opinion.score == 1
    assert "structured output failure" in opinion.argument


def test_negated_security_phrase_does_not_trigger_cap(monkeypatch) -> None:
    monkeypatch.setattr("src.nodes.judges._judge_llm", lambda: _NoConfirmedFlawsLLM())

    out = prosecutor(_state())
    opinion = out["opinions"][0]

    assert opinion.score == 5
    assert "Security claim not supported by evidence" not in opinion.argument


def test_absence_of_evidence_phrase_does_not_trigger_cap(monkeypatch) -> None:
    monkeypatch.setattr("src.nodes.judges._judge_llm", lambda: _AbsenceOfEvidenceLLM())

    out = prosecutor(_state())
    opinion = out["opinions"][0]

    assert opinion.score == 5
    assert "Security claim not supported by evidence" not in opinion.argument


def test_absence_of_any_confirmed_flaw_phrase_does_not_trigger_cap(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.nodes.judges._judge_llm", lambda: _AbsenceOfAnyConfirmedFlawLLM()
    )

    out = prosecutor(_state())
    opinion = out["opinions"][0]

    assert opinion.score == 5
    assert "Security claim not supported by evidence" not in opinion.argument
