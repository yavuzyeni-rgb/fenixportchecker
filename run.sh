#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -r requirements.txt -q
export PYTHONPATH="$PWD/src"
exec .venv/bin/python -m portgozu --no-browser "$@"
