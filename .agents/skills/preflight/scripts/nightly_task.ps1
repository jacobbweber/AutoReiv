<#
.SYNOPSIS
  Nightly preflight as a Windows scheduled task [CARD-560]. Opt-in: prints the plan unless -Register is given.

.DESCRIPTION
  Runs `preflight.py --nightly` (full tier + every live journey) from the repo root at the chosen time.
  Console output goes to %LOCALAPPDATA%\AutoReiv\nightly\run-<date>.log and the summary to
  %LOCALAPPDATA%\AutoReiv\nightly\<date>.md (never the repo). Do not register on Jarvis without Jacob.

.EXAMPLE
  pwsh -File .agents/skills/preflight/scripts/nightly_task.ps1              # print what would be registered
  pwsh -File .agents/skills/preflight/scripts/nightly_task.ps1 -Register    # register (Jacob only)
  pwsh -File .agents/skills/preflight/scripts/nightly_task.ps1 -Unregister  # remove it
#>
param(
    [string]$At = "02:30",
    [string]$TaskName = "AutoReiv Nightly Preflight",
    [switch]$Register,
    [switch]$Unregister
)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
$logDir = Join-Path $env:LOCALAPPDATA "AutoReiv\nightly"
$py = Join-Path $repo ".venv\Scripts\python.exe"
$inner = "Set-Location '$repo'; New-Item -ItemType Directory -Force '$logDir' | Out-Null; " +
         "& '$py' .agents/skills/preflight/scripts/preflight.py --nightly *> (Join-Path '$logDir' ('run-' + (Get-Date -Format yyyy-MM-dd) + '.log'))"
$taskArgs = "-NoProfile -WindowStyle Hidden -Command `"$inner`""

if ($Unregister) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed '$TaskName'."
    return
}

Write-Host "Task:    $TaskName (daily at $At, current user, only when logged on)"
Write-Host "Action:  pwsh $taskArgs"
Write-Host "Logs:    $logDir"
if (-not $Register) {
    Write-Host "Dry run. Re-run with -Register to create the task (ask Jacob first)."
    return
}
$action = New-ScheduledTaskAction -Execute "pwsh.exe" -Argument $taskArgs -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 3)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "AutoReiv preflight --nightly [CARD-560]" | Out-Null
Write-Host "Registered '$TaskName'."
