#!/usr/bin/env bash
# Backend tests (unittest; pytest also works). Run from the repo root with the venv active.
set -euo pipefail
cd "$(dirname "$0")/.."
python -m unittest discover -s tests -t . -v
