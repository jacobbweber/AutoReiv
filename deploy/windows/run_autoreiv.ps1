<#
.SYNOPSIS
    AutoReiv Native Windows Launcher Script
    [REQ-DEPLOY-004]
#>

[CmdletBinding()]
param (
    [string]$HostIP = "0.0.0.0",
    [int]$Port = 8000,
    [string]$DbPath = "$PSScriptRoot\..\..\data\autoreiv.db",
    [string]$WikiPath = "$PSScriptRoot\..\..\data\wiki",
    [switch]$Reload
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   🤖 Starting AutoReiv Control Plane on Windows" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Ensure data directories exist
$DataDir = Split-Path -Parent $DbPath
if (!(Test-Path $DataDir)) { New-Item -ItemType Directory -Path $DataDir -Force | Out-Null }
if (!(Test-Path $WikiPath)) { New-Item -ItemType Directory -Path $WikiPath -Force | Out-Null }

# Set Environment Variables
$env:AUTOREIV_DB_PATH = (Resolve-Path $DbPath).Path
$env:AUTOREIV_WIKI_PATH = (Resolve-Path $WikiPath).Path
$env:PORT = $Port.ToString()
$env:HOST = $HostIP

$RootPath = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $RootPath

# Detect Virtual Environment
$PythonExe = "python"
if (Test-Path "$RootPath\.venv\Scripts\python.exe") {
    $PythonExe = "$RootPath\.venv\Scripts\python.exe"
}

$ReloadFlag = if ($Reload) { "--reload" } else { "" }

Write-Host " • Database : $env:AUTOREIV_DB_PATH" -ForegroundColor Gray
Write-Host " • Wiki     : $env:AUTOREIV_WIKI_PATH" -ForegroundColor Gray
Write-Host " • Server   : http://$HostIP`:$Port" -ForegroundColor Green
Write-Host " • Python   : $PythonExe" -ForegroundColor Gray
Write-Host "------------------------------------------------------------" -ForegroundColor Cyan

& $PythonExe -m src.cli.main serve --host $HostIP --port $Port $ReloadFlag
