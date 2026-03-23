#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python scripts/run_quick_checks.py "$@"
