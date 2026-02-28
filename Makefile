SHELL := /usr/bin/env bash

.PHONY: install run audit self_audit peer_audit self_audit_archive peer_audit_archive format lint test clean
install:
	uv sync

run:
	uv run python -m src.run --help

# Defaults. Override from CLI.
REPO ?= https://github.com/NuryeNigusMekonen/Automation-Auditor.git
PDF  ?= ./reports/week2_takeaway.pdf
OUT  ?= ./audit/report_onself_generated/self_audit_run.md
RUBRIC ?= rubric/week2_rubric.json
ENABLE_VISION ?= 1
VERBOSE ?= 0
LOG_FILE ?=

audit:
	set -a; [ -f .env ] && source .env; set +a; \
	uv run python -m src.run \
		--repo "$(REPO)" \
		--pdf "$(PDF)" \
		--out "$(OUT)" \
		--rubric "$(RUBRIC)" \
		$(if $(filter 1 true TRUE yes YES,$(VERBOSE)),--verbose,) \
		$(if $(strip $(LOG_FILE)),--log-file "$(LOG_FILE)",) \
		$(if $(filter 1 true TRUE yes YES,$(ENABLE_VISION)),--enable-vision,)

self_audit:
	$(MAKE) audit \
		REPO="https://github.com/NuryeNigusMekonen/Automation-Auditor.git" \
		PDF="./reports/week2_takeaway.pdf" \
		OUT="./audit/report_onself_generated/self_audit_run.md"
	@cp ./audit/report_onself_generated/self_audit_run.md ./audit/report_onself_generated/self_audit.md

peer_audit:
	$(MAKE) audit \
		REPO="https://github.com/habeshacoder/Automaton-Auditor.git" \
		PDF="./reports/week2_takeaway.pdf" \
		OUT="./audit/report_onpeer_generated/habesha_audit_from_run.md"
	@cp ./audit/report_onpeer_generated/habesha_audit_from_run.md ./audit/report_onpeer_generated/habesha_audit.md

self_audit_archive:
	$(MAKE) self_audit
	@ts=$$(date -u +%Y%m%dT%H%M%SZ); \
	mkdir -p ./audit/archive; \
	cp ./audit/report_onself_generated/self_audit_run.md ./audit/archive/self_audit_$$ts.md; \
	echo "Archived: ./audit/archive/self_audit_$$ts.md"

peer_audit_archive:
	$(MAKE) peer_audit
	@ts=$$(date -u +%Y%m%dT%H%M%SZ); \
	mkdir -p ./audit/archive; \
	cp ./audit/report_onpeer_generated/habesha_audit_from_run.md ./audit/archive/peer_audit_$$ts.md; \
	echo "Archived: ./audit/archive/peer_audit_$$ts.md"

format:
	uv run python -m ruff format .

lint:
	uv run python -m ruff check .

test:
	uv run python -m pytest -q

clean:
	rm -rf .pytest_cache .ruff_cache **/__pycache__ .mypy_cache