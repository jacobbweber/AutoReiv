#!/usr/bin/env bash
# CARD-310: assemble UI + apply index panel + restart (run from anywhere)
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scratch/card310/assemble_routines_js.py
if ! grep -q routineStructuredSchedulePanel src/web/templates/index.html; then
  git apply scratch/card310/index_310.patch || patch -p1 < scratch/card310/index_310.patch
fi
python3 scripts/restart_serve.py --port 8000
echo "CARD-310 UI applied. Tip: $(git rev-parse --short HEAD). Ctrl+F5 Routines."
