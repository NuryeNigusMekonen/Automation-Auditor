## Architecture Node Contracts (Start to End)

Node contract format: Before -> Logic -> Decision -> After -> Next.

### 1) repo_investigator
- Before: repo_url, workspace_dir, rubric dimensions.
- Logic: clone repo safely; collect git history, graph AST, state-model, security, and file-index evidence.
- Decision: clone failure emits found=False evidence instead of crashing.
- After: emits git_forensic_analysis, graph_orchestration, state_management_rigor, safe_tool_engineering, repo_file_index.
- Next: evidence_aggregator.

### 2) doc_analyst
- Before: pdf_path.
- Logic: parse PDF and extract theoretical/report-accuracy evidence.
- Decision: PDF failure emits negative documentation evidence.
- After: emits theoretical_depth/report_accuracy bundles.
- Next: evidence_aggregator.

### 3) vision_inspector
- Before: pdf_path, enable_vision.
- Logic: analyze diagrams/images for architecture signals.
- Decision: disabled/unavailable vision emits fallback evidence.
- After: emits swarm_visual evidence.
- Next: evidence_aggregator.

### 4) evidence_aggregator
- Before: merged detective evidence map.
- Logic: normalize/enrich evidence (citation_pool, cross-reference, consistency, security_override_signal).
- Decision: security signal is deterministic from unsafe-hit markers.
- After: emits enriched evidence patch.
- Next: orchestration_guard.

### 5) orchestration_guard
- Before: aggregated evidences.
- Logic: check required key presence (git_forensic_analysis, graph_orchestration).
- Decision: missing key => fail; key present with found=False => pass.
- After: either orchestration_guard failure evidence or empty patch.
- Next: abort or judges_dispatch.

### 6) abort
- Before: guard-failed path only.
- Logic: write explicit guard-failure evidence.
- Decision: none.
- After: emits orchestration_guard trace evidence.
- Next: chief_justice.

### 7) judges_dispatch
- Before: guard-passed path only.
- Logic: routing fan-out to judges.
- Decision: none.
- After: routing-only handoff.
- Next: prosecutor, defense, tech_lead (parallel).

### 8) prosecutor
- Before: criterion + evidence bundle.
- Logic: adversarial risk-focused scoring.
- Decision: structured-output retry path on malformed responses.
- After: emits JudicialOpinion(Prosecutor).
- Next: opinions_aggregator.

### 9) defense
- Before: criterion + evidence bundle.
- Logic: effort/intent-aware scoring.
- Decision: structured-output retry path.
- After: emits JudicialOpinion(Defense).
- Next: opinions_aggregator.

### 10) tech_lead
- Before: criterion + evidence bundle.
- Logic: practical architecture/maintainability scoring.
- Decision: structured-output retry path.
- After: emits JudicialOpinion(TechLead).
- Next: opinions_aggregator.

### 11) opinions_aggregator
- Before: parallel judge opinions.
- Logic: summarize per-criterion opinion counts.
- Decision: always continue to synthesis.
- After: emits opinions_summary evidence.
- Next: chief_justice.

### 12) chief_justice
- Before: evidence map + opinions (or abort evidence).
- Logic: deterministic synthesis rules (security gate, fact supremacy, functionality weight, variance re-evaluation).
- Decision: apply caps/overrides only when rule conditions hold.
- After: emits final_report and final_report_markdown.
- Next: END.

## End-to-End Execution Steps
1. START fans out detectives: repo_investigator, doc_analyst, vision_inspector.
2. Detective outputs fan in at evidence_aggregator.
3. orchestration_guard validates minimum required evidence keys.
4. Guard fail path: abort -> chief_justice -> END.
5. Guard pass path: judges_dispatch -> parallel judges -> opinions_aggregator -> chief_justice -> END.
6. Final output is always structured, including guarded-abort runs.

