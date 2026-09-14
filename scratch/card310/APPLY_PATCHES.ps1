$ErrorActionPreference="Stop"
Set-Location "D:\Projects\Active\AutoReiv"
git fetch origin feat/super-marathon-ui
git checkout feat/super-marathon-ui
git pull --ff-only origin feat/super-marathon-ui
if (-not (Select-String -Path src\web\templates\index.html -Pattern "routineStructuredSchedulePanel" -Quiet)) {
  git apply --3way scratch/card310/index_310.patch
}
if (-not (Select-String -Path src\web\static\modules\studios\routines.js -Pattern "buildCreateAgentSelectList" -Quiet)) {
  git apply --3way scratch/card310/routines_js_310.patch
}
Write-Host "tip=$(git rev-parse --short HEAD)"
python scripts/restart_serve.py --port 8000
