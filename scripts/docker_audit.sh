#!/usr/bin/env bash
set -euo pipefail

PDF="${1:?pdf path required, example: reports/week2_takeaway.pdf}"
OUT="${2:?output path required, example: audit/report_onpeer_generated/habesha_audit.md}"
REPO="${3:?repo url required}"

# Run from repo root
ROOT="$(pwd)"

# Validate input pdf exists on host
if [ ! -f "$ROOT/$PDF" ]; then
  echo "PDF not found: $ROOT/$PDF"
  exit 1
fi

# Create output folder on host
mkdir -p "$ROOT/$(dirname "$OUT")"

docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
  -e LANGCHAIN_TRACING_V2="${LANGCHAIN_TRACING_V2:-true}" \
  -e LANGCHAIN_PROJECT="${LANGCHAIN_PROJECT:-automation-audit}" \
  -e LANGSMITH_API_KEY="${LANGSMITH_API_KEY:-}" \
  -v "$ROOT:/work" \
  -w /work \
  automation-auditor \
  sh -lc "mkdir -p \"$(dirname "/work/$OUT")\" && python -m src.run --repo \"$REPO\" --pdf \"/work/$PDF\" --out \"/work/$OUT\""

echo "Host wrote: $ROOT/$OUT"
ls -la "$ROOT/$(dirname "$OUT")" | sed -n '1,10p'
