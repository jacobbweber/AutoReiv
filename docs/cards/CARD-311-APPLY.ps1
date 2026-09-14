# CARD-311: apply Observe HTML + forge telemetry patches on Jarvis checkout.
# Run from repo root: D:\Projects\Active\AutoReiv
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..\..
git apply --whitespace=nowarn docs/cards/CARD-311-index.html.patch
git apply --whitespace=nowarn docs/cards/CARD-311-forge.js.patch
Write-Host "CARD-311 patches applied. Ctrl+F5. uv.lock may stay dirty."
