# CARD-319 fold on Jarvis (if tip missing product delta)
$ErrorActionPreference = "Stop"
Set-Location "D:\Projects\Active\AutoReiv"
git fetch origin feat/education-retention-319
git checkout feat/education-retention-319
git pull --ff-only origin feat/education-retention-319
if (Test-Path "docs\cards\CARD-319-APPLY.patch") {
  git apply --whitespace=nowarn "docs\cards\CARD-319-APPLY.patch"
}
Write-Host "CARD-319 APPLY done. Leave uv.lock dirty. Restart serve + Ctrl+F5."
