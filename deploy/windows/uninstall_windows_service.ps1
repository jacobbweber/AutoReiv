<#
.SYNOPSIS
    Windows Service Uninstallation Script for AutoReiv
    [REQ-DEPLOY-004], [CARD-670]
    Stops and unregisters the service only. It never deletes the data folder.
#>

[CmdletBinding()]
param (
    [string]$ServiceName = "AutoReivService",
    [string]$DataDir = ""
)

$ErrorActionPreference = "Stop"

# Ensure Admin Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Please run this script from an elevated PowerShell Administrator console."
    exit 1
}

Write-Host "Uninstalling AutoReiv Windows Service ($ServiceName)..." -ForegroundColor Cyan

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue

# Read the data folder the service used before it is unregistered. This script never deletes it.
if ([string]::IsNullOrWhiteSpace($DataDir) -and $svc) {
    $nssmCmd = Get-Command nssm -ErrorAction SilentlyContinue
    if ($nssmCmd) {
        $extra = (& nssm get $ServiceName AppEnvironmentExtra 2>$null) -join "`n"
        $m = [regex]::Match($extra, 'AUTOREIV_DATA_DIR=([^\r\n]+)')
        if ($m.Success) { $DataDir = $m.Groups[1].Value.Trim() }
    }
}

if ($svc) {
    Write-Host " - Service found with status: $($svc.Status)" -ForegroundColor Yellow

    # Stop service if running
    if ($svc.Status -eq 'Running' -or $svc.Status -eq 'StartPending') {
        Write-Host " - Stopping service..." -ForegroundColor Yellow
        $nssm = Get-Command nssm -ErrorAction SilentlyContinue
        if ($nssm) {
            & nssm stop $ServiceName
        } else {
            Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
    }

    # Remove / unregister service
    Write-Host " - Removing service registration..." -ForegroundColor Yellow
    $nssm = Get-Command nssm -ErrorAction SilentlyContinue
    if ($nssm) {
        & nssm remove $ServiceName confirm
    } else {
        & sc.exe delete $ServiceName
    }

    Write-Host "OK: AutoReiv Windows Service ($ServiceName) successfully uninstalled!" -ForegroundColor Green
} else {
    Write-Host "Note: No registered Windows service named '$ServiceName' was found." -ForegroundColor Yellow
}

if ([string]::IsNullOrWhiteSpace($DataDir)) {
    $DataDir = if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "AutoReiv" } else { "user data" }
}
Write-Host "Kept: User database and workspace data at '$DataDir' were preserved." -ForegroundColor Cyan
