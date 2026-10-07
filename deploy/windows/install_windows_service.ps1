<#
.SYNOPSIS
    Windows Service Setup Script for AutoReiv using NSSM (Non-Sucking Service Manager)
    [REQ-DEPLOY-004], [CARD-670]
.DESCRIPTION
    Registers AutoReiv as a Windows service. -DataDir sets AUTOREIV_DATA_DIR on the service;
    the default is %LOCALAPPDATA%\AutoReiv for the installing user. Service logs go to <DataDir>\logs.
.EXAMPLE
    .\deploy\windows\install_windows_service.ps1
.EXAMPLE
    .\deploy\windows\install_windows_service.ps1 -ServiceName AutoReivTest -Port 8780 -DataDir D:\AutoReiv-test
#>

[CmdletBinding()]
param (
    [string]$ServiceName = "AutoReivService",
    [string]$Port = "8000",
    [string]$DataDir = ""
)

$ErrorActionPreference = "Stop"

# Ensure Admin Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Please run this script from an elevated PowerShell Administrator console."
    exit 1
}

if ([string]::IsNullOrWhiteSpace($DataDir)) {
    $DataDir = Join-Path $env:LOCALAPPDATA "AutoReiv"
}
$DataDir = [System.IO.Path]::GetFullPath($DataDir)
$LogDir = Join-Path $DataDir "logs"
New-Item -ItemType Directory -Force -Path $DataDir, $LogDir | Out-Null

$RootPath = (Resolve-Path "$PSScriptRoot\..\..").Path
$PythonExe = "$RootPath\.venv\Scripts\python.exe"
if (!(Test-Path $PythonExe)) {
    $PythonExe = (Get-Command python.exe).Source
}

Write-Host "📦 Setting up AutoReiv as a persistent Windows background service..." -ForegroundColor Cyan
Write-Host " • Service Name: $ServiceName"
Write-Host " • Python Path : $PythonExe"
Write-Host " • Working Dir : $RootPath"
Write-Host " • Data Dir    : $DataDir"

# Check if nssm is available
$nssm = Get-Command nssm -ErrorAction SilentlyContinue

if ($nssm) {
    Write-Host "Found NSSM, configuring service..." -ForegroundColor Green
    $ServiceEnv = "AUTOREIV_DATA_DIR=$DataDir"
    & nssm install $ServiceName $PythonExe "-m src.cli.main serve --host 0.0.0.0 --port $Port"
    & nssm set $ServiceName AppDirectory $RootPath
    & nssm set $ServiceName AppEnvironmentExtra $ServiceEnv
    & nssm set $ServiceName AppStdout (Join-Path $LogDir "autoreiv_service.log")
    & nssm set $ServiceName AppStderr (Join-Path $LogDir "autoreiv_error.log")
    & nssm set $ServiceName Start SERVICE_AUTO_START
    & nssm start $ServiceName
    Write-Host "✅ AutoReiv Windows Service successfully created and started!" -ForegroundColor Green
    Write-Host " • Data Dir   : $DataDir (kept by the uninstaller)" -ForegroundColor Cyan
    Write-Host " • Uninstaller: .\deploy\windows\uninstall_windows_service.ps1 -ServiceName $ServiceName" -ForegroundColor Cyan
} else {
    Write-Warning "NSSM is not installed. To register as a native Windows service automatically, install NSSM via 'winget install nssm' or 'choco install nssm' and re-run this script."
    Write-Host ""
    Write-Host "Alternatively, use the background runner: .\deploy\windows\run_autoreiv.ps1 -DataDir `"$DataDir`"" -ForegroundColor Yellow
}
