#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python scratch/card310/assemble_routines_js.py
if ! grep -q routineStructuredSchedulePanel src/web/templates/index.html; then
  git apply scratch/card310/index_310.patch || patch -p1 < scratch/card310/index_310.patch
fi
python scripts/restart_serve.py --port 8000
