#!/usr/bin/env bash
set -euo pipefail

python -m src.run --help >/dev/null

exec python -m src.run "$@"
