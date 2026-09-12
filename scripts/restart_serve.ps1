# CARD-256: thin Jarvis wrapper around scripts/restart_serve.py
param(
    [int]$Port = 8000,
    [string]$HostAddr = "127.0.0.1",
    [switch]$DryRun,
    [switch]$KillOnly,
    [switch]$Status,
    [switch]$NoWait
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Root "src\web\templates\index.html"))) {
    $Root = (Get-Location).Path
}
Set-Location $Root
$argsList = @("scripts/restart_serve.py", "--port", "$Port", "--host", $HostAddr)
if ($DryRun) { $argsList += "--dry-run" }
if ($KillOnly) { $argsList += "--kill-only" }
if ($Status) { $argsList += "--status" }
if ($NoWait) { $argsList += "--no-wait" }
& uv run python @argsList
exit $LASTEXITCODE
