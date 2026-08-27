#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=.
python3 -m pip install -q -r requirements.txt
python3 -m varma.routines.run_brief
exec python3 -m varma
