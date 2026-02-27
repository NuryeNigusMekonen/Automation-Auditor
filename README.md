# Automation Auditor

Digital Courtroom Multi-Agent Evaluator 

## Overview

Automation Auditor is a hierarchical, production-grade LangGraph system that evaluates a GitHub repository and an architectural PDF using a Digital Courtroom model.

The system performs structured forensic analysis, applies dialectical judicial reasoning, and generates a deterministic, actionable audit report in Markdown format.

This is not a single-prompt grader. It is a multi-agent swarm with explicit role separation, typed state management, and constitutional governance.

---

## Architectural Model: The Digital Courtroom

The system is built as a three-layer hierarchical state graph.

### Layer 1 - Detective Layer (Forensic Sub-Agents)

These agents collect objective evidence only. They do not score or opinionate.

* RepoInvestigator

  * Analyzes Git history
  * Verifies typed state definitions
  * Parses AST to inspect graph wiring
  * Validates sandboxed tooling

* DocAnalyst

  * Parses PDF report
  * Checks theoretical depth
  * Cross-references claims against actual repository structure

* VisionInspector (optional)

  * Extracts images from PDF
  * Classifies diagram type
  * Verifies presence of parallel fan-out / fan-in architecture

Output: Structured Evidence objects stored in typed state.

---

### Layer 2 - Judicial Layer (Dialectical Bench)

Three independent personas evaluate the same evidence for each rubric criterion.

* Prosecutor
  Philosophy: Trust no one. Assume structural weakness.
  Focus: Security flaws, orchestration fraud, hallucination liability.

* Defense
  Philosophy: Reward engineering effort and intent.
  Focus: Depth of reasoning, iteration history, architectural insight.

* Tech Lead
  Philosophy: Does it work? Is it maintainable?
  Focus: State reducers, safety boundaries, practical viability.

Each judge produces structured JudicialOpinion objects using enforced JSON schema validation.

Parallel fan-out ensures independent reasoning before synthesis.

---

### Layer 3 - Supreme Court (Synthesis Engine)

The ChiefJusticeNode resolves conflicts using deterministic rules.

It does not average scores blindly.

Hardcoded rules include:

* Security Override
* Fact Supremacy
* Variance-based re-evaluation
* Dissent summary requirement

Output: Structured Markdown Audit Report containing:

* Executive Summary
* Criterion Breakdown
* Conflict Analysis
* Remediation Plan

---

## State Management

State is strictly typed using:

* Pydantic BaseModel
* TypedDict
* Explicit reducers (operator.add, operator.ior)

This prevents data overwriting during parallel execution.

No untyped dictionary passing is allowed.

---

## The Rubric as Constitution

The file:

rubric/week2_rubric.json

Defines:

* Forensic instructions for detectives
* Persona-specific judicial logic
* Synthesis rules

The swarm dynamically loads this file at runtime.

This allows governance updates without code changes.

---

## Graph Orchestration

The LangGraph workflow enforces:

Detectives (Parallel Fan-Out)
→ Evidence Aggregation (Fan-In)
→ Judges (Parallel Fan-Out)
→ Chief Justice (Deterministic Synthesis)
→ Final Markdown Report

This ensures architectural rigor and prevents linear single-prompt grading.

### Execution Diagram

```mermaid
flowchart TD
  S([START])

  S --> RI[repo_investigator]
  S --> DA[doc_analyst]
  S --> VI[vision_inspector]

  RI --> EA[evidence_aggregator]
  DA --> EA
  VI --> EA

  EA --> OG[orchestration_guard]

  OG -->|guard failed| AB[abort]
  AB --> CJ[chief_justice]

  OG -->|guard passed| JD[judges_dispatch]
  JD --> PR[prosecutor]
  JD --> DE[defense]
  JD --> TL[tech_lead]

  PR --> OA[opinions_aggregator]
  DE --> OA
  TL --> OA

  OA --> CJ
  CJ --> E([END])
```

---

## Installation

Recommended workflow (uv):

```bash
uv sync
source .venv/bin/activate
```

Create `.env` in project root:

```bash
cp .env.example .env
```

Set required key:

```bash
OPENAI_API_KEY=your_key_here
```

Optional:

```bash
OPENAI_MODEL=gpt-4o-mini
```

Do not commit `.env`.

---

## Usage

Run the auditor:

```bash
uv run python -m src.run \
  --repo <github_repo_url> \
  --pdf <path_to_pdf> \
  --out <output_markdown_path>
```

Example:

```bash
uv run python -m src.run \
  --repo https://github.com/user/project \
  --pdf ./reports/week2_takeaway.pdf \
  --out ./audit/report_onpeer_generated/peer_audit.md \
  --rubric ./rubric/week2_rubric.json \
  --enable-vision

# Offline deterministic mode (no LLM calls)
uv run python -m src.run \
  --repo https://github.com/user/project \
  --pdf ./reports/week2_takeaway.pdf \
  --out ./audit/report_onpeer_generated/peer_audit_offline.md \
  --offline
```

Generated audit report:

`audit/report_onpeer_generated/`

Convenience targets:

```bash
make self_audit
make peer_audit
```

Runtime caps (optional):

```bash
AUDITOR_CAP_REPORT_PATHS=1500
AUDITOR_CAP_ALLOWED_CITATIONS=40
AUDITOR_CAP_EVIDENCE_ITEMS=60
```


---

## Engineering Decisions

* AST parsing instead of regex for structural verification
* Sandboxed git cloning via tempfile isolation
* Strict structured output enforcement for judges
* Deterministic conflict resolution in synthesis layer
* Typed state reducers to protect parallel execution

---

## Production Considerations

* Token usage optimized by limiting evidence packet size
* Structured retry policy for invalid LLM JSON output
* Configurable parallelism
* Usage limits recommended for API cost control

---

## Production Operations

### Required Environment Variables

Set these in your deployment environment:

```bash
OPENAI_API_KEY=<required>
OPENAI_MODEL=gpt-4o-mini
```

Optional operational controls:

```bash
AUDITOR_OFFLINE_MODE=false
AUDITOR_CAP_REPORT_PATHS=2000
AUDITOR_CAP_ALLOWED_CITATIONS=50
AUDITOR_CAP_EVIDENCE_ITEMS=80
```

### Runtime Packaging and Startup

Container runtime includes:

* Pinned Python runtime image (`python:3.12.8-slim-bookworm`)
* Non-root execution user (`appuser`)
* Healthcheck (`python -m src.run --help`)
* Startup smoke command in container entrypoint before launching requested args

### SLO Targets

Recommended baseline SLOs:

* Availability: 99.5% monthly for audit execution endpoint/job runner
* Successful run rate: >= 98% of scheduled/on-demand audits
* P95 audit completion latency: <= 5 minutes for standard rubric + medium repo
* False-start rate (startup/config failures): < 1%

### Common Failure Modes

Typical production failure classes:

* Missing or invalid env vars (e.g., `OPENAI_API_KEY` absent)
* Rubric schema validation failure (missing required keys)
* External dependency failure (GitHub clone/network/LLM API timeout)
* Input artifact issues (missing PDF, unreadable PDF, malformed repo URL)
* Rate limiting or quota exhaustion from model provider

### Incident Response Steps

Use this runbook for first response:

1. Confirm deployment health (`docker ps`, health status, CI status).
2. Check startup smoke output and application logs for configuration errors.
3. Validate critical env vars and rubric file integrity.
4. Re-run failing command in deterministic mode for triage:

  ```bash
  uv run python -m src.run --repo <repo> --pdf <pdf> --out <out> --offline
  ```

5. If offline succeeds but online fails, treat as external/API incident (provider or network).
6. If both fail, isolate to local parsing/schema/runtime logic and roll back to previous known-good commit if needed.
7. Document impact, timeline, root cause, and corrective action in post-incident notes.

---

## Future Improvements

* Add CI integration for automated PR auditing
* Add caching layer for repository analysis
* Expand diagram reasoning capabilities
* Add policy versioning for rubric updates

---

## Educational Objective

This project demonstrates:

* Multi-agent orchestration
* Governance via machine-readable constitution
* Separation of facts and interpretation
* Deterministic synthesis over stochastic reasoning
* Production-grade architectural thinking

---