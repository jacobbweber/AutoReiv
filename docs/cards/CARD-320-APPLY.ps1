# CARD-320 apply on Jarvis (D:\Projects\Active\AutoReiv)
# After: git fetch + checkout feat/education-studio-finish + pull
$ErrorActionPreference = "Stop"
Set-Location "D:\Projects\Active\AutoReiv"
git fetch origin feat/education-studio-finish
git checkout feat/education-studio-finish
git pull --ff-only origin feat/education-studio-finish
# Apply agent_memory course wiring if not already present:
if (Test-Path "docs\cards\CARD-320-agent_memory.patch") {
  git apply --whitespace=nowarn "docs\cards\CARD-320-agent_memory.patch" 2>$null
  Write-Host "agent_memory patch attempted"
}
# If product files still missing (router/js/html/tests/CHANGELOG), restore from CARD320_bundle.tgz next to this script:
$bundle = Join-Path $PSScriptRoot "CARD320_bundle.tgz"
if (Test-Path $bundle) {
  tar -xzf $bundle
  Write-Host "Restored CARD-320 files from bundle"
}
# Fold Unreleased from CARD-320-CHANGELOG-SNIPPET.md if needed
# Leave uv.lock dirty
python scripts/restart_serve.py --port 8000
Write-Host "Ctrl+F5 Education Studio — course chrome + Jump to step; no Dual Coding player"
