.PHONY: install run audit self_audit peer_audit format lint test clean
ENV_RUN = bash -lc 'set -a; [ -f .env ] && source .env; set +a; '
install:
	uv sync

run:
	uv run python -m src.run --help

# Defaults. Override from CLI.
REPO ?= https://github.com/NuryeNigusMekonen/Automation-Auditor.git
PDF  ?= ./reports/week2_takeaway.pdf
OUT  ?= ./audit/report_onself_generated/self_audit.md
RUBRIC ?= rubric/week2_rubric.json
ENABLE_VISION ?= 1

audit:
	$(ENV_RUN) uv run python -m src.run \
		--repo "$(REPO)" \
		--pdf "$(PDF)" \
		--out "$(OUT)" \
		--rubric "$(RUBRIC)" \
		$(if $(filter 1 true TRUE yes YES,$(ENABLE_VISION)),--enable-vision,)

self_audit:
	$(MAKE) audit \
		REPO="https://github.com/NuryeNigusMekonen/Automation-Auditor.git" \
		PDF="./reports/week2_takeaway.pdf" \
		OUT="./audit/report_onself_generated/self_audit.md"

peer_audit:
	$(MAKE) audit \
		REPO="https://github.com/habeshacoder/Automaton-Auditor.git" \
		PDF="./reports/week2_takeaway.pdf" \
		OUT="./audit/report_onpeer_generated/habesha_audit.md"

format:
	uv run python -m ruff format .

lint:
	uv run python -m ruff check .

test:
	uv run python -m pytest -q

clean:
	rm -rf .pytest_cache .ruff_cache **/__pycache__ .mypy_cache