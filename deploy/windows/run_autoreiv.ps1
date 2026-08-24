<#
.SYNOPSIS
    AutoReiv Native Windows Launcher Script
    [REQ-DEPLOY-004]
#>

[CmdletBinding()]
param (
    [string]$HostIP = "0.0.0.0",
    [int]$Port = 8000,
    [string]$DbPath = "",
    [string]$WikiPath = "",
    [switch]$Reload
)

$ErrorActionPreference = "Stop"

# Determine Repository Root Path
$RootPath = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $RootPath

if ([string]::IsNullOrWhiteSpace($DbPath)) {
    $DbPath = Join-Path $RootPath "data\autoreiv.db"
}
if ([string]::IsNullOrWhiteSpace($WikiPath)) {
    $WikiPath = Join-Path $RootPath "data\wiki"
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   🤖 Starting AutoReiv Control Plane on Windows" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Ensure data directories exist
$DataDir = Split-Path -Parent $DbPath
if (!(Test-Path $DataDir)) { New-Item -ItemType Directory -Path $DataDir -Force | Out-Null }
if (!(Test-Path $WikiPath)) { New-Item -ItemType Directory -Path $WikiPath -Force | Out-Null }

# Set Environment Variables
$env:AUTOREIV_DB_PATH = $DbPath
$env:AUTOREIV_WIKI_PATH = $WikiPath
$env:PORT = $Port.ToString()
$env:HOST = $HostIP
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# Detect Virtual Environment / Active Python
$PythonExe = "python"

if ($env:VIRTUAL_ENV -and (Test-Path (Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"))) {
    $PythonExe = Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
} elseif ($env:CONDA_PREFIX -and (Test-Path (Join-Path $env:CONDA_PREFIX "python.exe"))) {
    $PythonExe = Join-Path $env:CONDA_PREFIX "python.exe"
} elseif (Test-Path "$RootPath\.venv\Scripts\uvicorn.exe") {
    $PythonExe = "$RootPath\.venv\Scripts\python.exe"
}


Write-Host " • Database : $env:AUTOREIV_DB_PATH" -ForegroundColor Gray
Write-Host " • Wiki     : $env:AUTOREIV_WIKI_PATH" -ForegroundColor Gray
Write-Host " • Local UI : http://localhost`:$Port" -ForegroundColor Green
Write-Host " • LAN UI   : http://$HostIP`:$Port" -ForegroundColor Green
Write-Host " • Python   : $PythonExe" -ForegroundColor Gray
Write-Host "------------------------------------------------------------" -ForegroundColor Cyan

$cmdArgs = @("-m", "src.cli.main", "serve", "--host", $HostIP, "--port", $Port.ToString(), "--db-path", $DbPath, "--wiki-path", $WikiPath)
if ($Reload) { $cmdArgs += "--reload" }

& $PythonExe $cmdArgs

