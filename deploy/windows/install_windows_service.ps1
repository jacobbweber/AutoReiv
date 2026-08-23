<#
.SYNOPSIS
    Windows Service Setup Script for AutoReiv using NSSM (Non-Sucking Service Manager)
    [REQ-DEPLOY-004]
#>

[CmdletBinding()]
param (
    [string]$ServiceName = "AutoReivService",
    [string]$Port = "8000"
)

$ErrorActionPreference = "Stop"

# Ensure Admin Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Please run this script from an elevated PowerShell Administrator console."
    exit 1
}

$RootPath = (Resolve-Path "$PSScriptRoot\..\..").Path
$PythonExe = "$RootPath\.venv\Scripts\python.exe"
if (!(Test-Path $PythonExe)) {
    $PythonExe = (Get-Command python.exe).Source
}

Write-Host "📦 Setting up AutoReiv as a persistent Windows background service..." -ForegroundColor Cyan
Write-Host " • Service Name: $ServiceName"
Write-Host " • Python Path : $PythonExe"
Write-Host " • Working Dir : $RootPath"

# Check if nssm is available
$nssm = Get-Command nssm -ErrorAction SilentlyContinue

if ($nssm) {
    Write-Host "Found NSSM, configuring service..." -ForegroundColor Green
    & nssm install $ServiceName $PythonExe "-m src.cli.main serve --host 0.0.0.0 --port $Port"
    & nssm set $ServiceName AppDirectory $RootPath
    & nssm set $ServiceName AppStdout "$RootPath\data\autoreiv_service.log"
    & nssm set $ServiceName AppStderr "$RootPath\data\autoreiv_error.log"
    & nssm set $ServiceName Start SERVICE_AUTO_START
    & nssm start $ServiceName
    Write-Host "✅ AutoReiv Windows Service successfully created and started!" -ForegroundColor Green
} else {
    Write-Warning "NSSM is not installed. To register as a native Windows service automatically, install NSSM via 'winget install nssm' or 'choco install nssm' and re-run this script."
    Write-Host ""
    Write-Host "Alternatively, use the background runner: .\deploy\windows\run_autoreiv.ps1" -ForegroundColor Yellow
}
