$ErrorActionPreference="Stop"
Set-Location "D:\Projects\Active\AutoReiv"
git fetch origin feat/super-marathon-ui
git checkout feat/super-marathon-ui
git pull --ff-only origin feat/super-marathon-ui
Write-Host "tip=$(git rev-parse --short HEAD)"
python scripts/restart_serve.py --port 8000
Write-Host "Ctrl+F5 checklist: Routines > New Routine > structured panel (months/weekdays/DOM/time/every-N/anchor); both agent dropdowns list ALL /api/agents; save biweekly Tue 18:00 with anchor; see next_run_at; Pause blocks."
