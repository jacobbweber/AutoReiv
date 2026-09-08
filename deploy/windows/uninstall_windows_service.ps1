<#
.SYNOPSIS
    Windows Service Uninstallation Script for AutoReiv
    [REQ-DEPLOY-004]
#>

[CmdletBinding()]
param (
    [string]$ServiceName = "AutoReivService"
)

$ErrorActionPreference = "Stop"

# Ensure Admin Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Please run this script from an elevated PowerShell Administrator console."
    exit 1
}

Write-Host "🛑 Uninstalling AutoReiv Windows Service ($ServiceName)..." -ForegroundColor Cyan

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue

if ($svc) {
    Write-Host " • Service found with status: $($svc.Status)" -ForegroundColor Yellow

    # Stop service if running
    if ($svc.Status -eq 'Running' -or $svc.Status -eq 'StartPending') {
        Write-Host " • Stopping service..." -ForegroundColor Yellow
        $nssm = Get-Command nssm -ErrorAction SilentlyContinue
        if ($nssm) {
            & nssm stop $ServiceName
        } else {
            Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
    }

    # Remove / unregister service
    Write-Host " • Removing service registration..." -ForegroundColor Yellow
    $nssm = Get-Command nssm -ErrorAction SilentlyContinue
    if ($nssm) {
        & nssm remove $ServiceName confirm
    } else {
        & sc.exe delete $ServiceName
    }

    Write-Host "✅ AutoReiv Windows Service ($ServiceName) successfully uninstalled!" -ForegroundColor Green
} else {
    Write-Host "ℹ️  No registered Windows service named '$ServiceName' was found." -ForegroundColor Yellow
}

$DataDir = if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "AutoReiv" } else { "user data" }
Write-Host "🔒 User database and workspace data at '$DataDir' were preserved." -ForegroundColor Cyan
