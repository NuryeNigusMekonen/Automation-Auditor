.PHONY: install run self_audit format lint test clean

install:
	uv sync

run:
	python -m src.run --help

self_audit:
	python -m src.run \
		--repo https://github.com/NuryeNigusMekonen/Automation-Auditor.git \
		--pdf ./reports/week2_takeaway.pdf \
		--out ./audit/report_onself_generated/self_audit.md

format:
	python -m ruff format .

lint:
	python -m ruff check .

test:
	python -m pytest -q

clean:
	rm -rf .pytest_cache .ruff_cache **/__pycache__ .mypy_cache