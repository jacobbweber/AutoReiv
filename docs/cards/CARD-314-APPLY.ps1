$ErrorActionPreference='Stop'
Set-Location 'D:\Projects\Active\AutoReiv'
git fetch origin feat/super-marathon-ui
git checkout feat/super-marathon-ui
git pull --ff-only origin feat/super-marathon-ui
# If UI not fully on tip yet, apply local patch from docs or bundle
if (-not (Select-String -Path 'src\web\templates\index.html' -Pattern 'CARD-314: Factory train modal scrolls' -Quiet)) {
  if (Test-Path 'docs\cards\CARD-314-APPLY.patch') {
    git apply --whitespace=nowarn 'docs\cards\CARD-314-APPLY.patch'
  }
  $bundle = Join-Path $PSScriptRoot 'CARD314_bundle.tgz'
  if (Test-Path $bundle) { tar -xzf $bundle -C . }
}
# Ensure new files from tip
git add -A
# Do not stage uv.lock
git restore --staged uv.lock 2>$null
git status -sb
if (git diff --cached --quiet) { Write-Host 'nothing to commit (already applied?)' } else {
  git commit -m "fix(factory): CARD-314 train popup scroll + Factory min-h-0"
  git push origin feat/super-marathon-ui
}
Write-Host "tip=$(git rev-parse --short HEAD)"
# Kill :8000 listeners
netstat -ano | Select-String ':8000\s' | ForEach-Object {
  if ($_ -match '\s+(\d+)\s*$') {
    $procId = $Matches[1]
    if ($procId -and $procId -ne '0') { taskkill /F /PID $procId 2>$null }
  }
}
python scripts/restart_serve.py --port 8000
Start-Sleep -Seconds 2
$html = (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/).Content
@('CARD-314: Factory train modal scrolls','max-h-[90vh]','overflow-y-auto') | ForEach-Object {
  if ($html -notmatch [regex]::Escape($_)) { Write-Warning "MISSING in HTML: $_" } else { Write-Host "OK HTML: $_" }
}
$fj = Get-Content 'src\web\static\modules\studios\factory.js' -Raw
if ($fj -match 'openFactoryStudioForAgent') { Write-Host 'OK openFactoryStudioForAgent' } else { Write-Warning 'MISSING openFactoryStudioForAgent' }
Write-Host 'Ctrl+F5: Train modal scroll to Launch; Agents Open Training Factory = full studio window scoped to agent; app.js?v=2.0.50'
