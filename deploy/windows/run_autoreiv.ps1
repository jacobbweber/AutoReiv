<#
.SYNOPSIS
    AutoReiv Native Windows Launcher Script
    [REQ-DEPLOY-004], [REQ-DATA-001]
#>

[CmdletBinding()]
param (
    [string]$HostIP = "0.0.0.0",
    [int]$Port = 8000,
    [string]$DataDir = "",
    [string]$DbPath = "",
    [string]$WikiPath = "",
    [switch]$Reload
)

$ErrorActionPreference = "Stop"

# Determine Repository Root Path
$RootPath = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $RootPath

function Test-SameFsPath {
    param([string]$Left, [string]$Right)
    if ([string]::IsNullOrWhiteSpace($Left) -or [string]::IsNullOrWhiteSpace($Right)) {
        return $false
    }
    try {
        $a = [System.IO.Path]::GetFullPath($Left.Trim())
        $b = [System.IO.Path]::GetFullPath($Right.Trim())
        return ($a -ieq $b)
    } catch {
        return $false
    }
}

# CARD-102: checkout ./data is a migrate source, not a default override.
$LegacyDb = Join-Path $RootPath "data\autoreiv.db"
$LegacyWiki = Join-Path $RootPath "data\wiki"

if ([string]::IsNullOrWhiteSpace($DataDir)) {
    $DataDir = [string]$env:AUTOREIV_DATA_DIR
}
if ([string]::IsNullOrWhiteSpace($DbPath)) {
    $DbPath = [string]$env:AUTOREIV_DB_PATH
}
if ([string]::IsNullOrWhiteSpace($WikiPath)) {
    $WikiPath = [string]$env:AUTOREIV_WIKI_PATH
}

if (Test-SameFsPath $DbPath $LegacyDb) {
    $DbPath = ""
}
if (Test-SameFsPath $WikiPath $LegacyWiki) {
    $WikiPath = ""
}

# Drop leftover checkout env so the child process does not inherit a fake override.
if (Test-SameFsPath ([string]$env:AUTOREIV_DB_PATH) $LegacyDb) {
    Remove-Item Env:\AUTOREIV_DB_PATH -ErrorAction SilentlyContinue
}
if (Test-SameFsPath ([string]$env:AUTOREIV_WIKI_PATH) $LegacyWiki) {
    Remove-Item Env:\AUTOREIV_WIKI_PATH -ErrorAction SilentlyContinue
}

if (-not [string]::IsNullOrWhiteSpace($DataDir)) {
    $env:AUTOREIV_DATA_DIR = $DataDir
}
if (-not [string]::IsNullOrWhiteSpace($DbPath)) {
    $env:AUTOREIV_DB_PATH = $DbPath
}
if (-not [string]::IsNullOrWhiteSpace($WikiPath)) {
    $env:AUTOREIV_WIKI_PATH = $WikiPath
}

$env:PORT = $Port.ToString()
$env:HOST = $HostIP
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# Display: DataDirResolver platform default when the operator did not pass --data-dir
$DisplayRoot = $DataDir
if ([string]::IsNullOrWhiteSpace($DisplayRoot)) {
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        $DisplayRoot = Join-Path $env:LOCALAPPDATA "AutoReiv"
    } elseif (-not [string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
        $DisplayRoot = Join-Path $env:USERPROFILE ".autoreiv"
    } else {
        $DisplayRoot = "(DataDirResolver)"
    }
}
$DisplayDb = if (-not [string]::IsNullOrWhiteSpace($DbPath)) { $DbPath } else { Join-Path $DisplayRoot "autoreiv.db" }
$DisplayWiki = if (-not [string]::IsNullOrWhiteSpace($WikiPath)) { $WikiPath } else { Join-Path $DisplayRoot "wiki" }

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Starting AutoReiv Control Plane on Windows" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Detect Virtual Environment / Active Python
$PythonExe = "python"

if ($env:VIRTUAL_ENV -and (Test-Path (Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"))) {
    $PythonExe = Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
} elseif ($env:CONDA_PREFIX -and (Test-Path (Join-Path $env:CONDA_PREFIX "python.exe"))) {
    $PythonExe = Join-Path $env:CONDA_PREFIX "python.exe"
} elseif (Test-Path "$RootPath\.venv\Scripts\uvicorn.exe") {
    $PythonExe = "$RootPath\.venv\Scripts\python.exe"
}

Write-Host "  Data dir : $DisplayRoot" -ForegroundColor Gray
Write-Host "  Database : $DisplayDb" -ForegroundColor Gray
Write-Host "  Wiki     : $DisplayWiki" -ForegroundColor Gray
Write-Host "  Skills   : $(Join-Path $DisplayRoot 'skills')" -ForegroundColor Gray
Write-Host "  Local UI : http://localhost`:$Port" -ForegroundColor Green
Write-Host "  LAN UI   : http://$HostIP`:$Port" -ForegroundColor Green
Write-Host "  Python   : $PythonExe" -ForegroundColor Gray
Write-Host "------------------------------------------------------------" -ForegroundColor Cyan

# Do not pass checkout ./data as --db-path/--wiki-path. Explicit overrides only.
$cmdArgs = @("-m", "src.cli.main", "serve", "--host", $HostIP, "--port", $Port.ToString())
if (-not [string]::IsNullOrWhiteSpace($DataDir)) {
    $cmdArgs += @("--data-dir", $DataDir)
}
if (-not [string]::IsNullOrWhiteSpace($DbPath)) {
    $cmdArgs += @("--db-path", $DbPath)
}
if (-not [string]::IsNullOrWhiteSpace($WikiPath)) {
    $cmdArgs += @("--wiki-path", $WikiPath)
}
if ($Reload) { $cmdArgs += "--reload" }

& $PythonExe $cmdArgs
