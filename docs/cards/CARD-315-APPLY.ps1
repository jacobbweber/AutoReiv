$ErrorActionPreference='Stop'
Set-Location 'D:\Projects\Active\AutoReiv'
git fetch origin feat/super-marathon-ui
git checkout feat/super-marathon-ui
git pull --ff-only origin feat/super-marathon-ui
if (-not (Select-String -Path 'src\web\templates\index.html' -Pattern 'CARD-315: Education sections collapse \+ scroll' -Quiet)) {
  if (Test-Path 'docs\cards\CARD-315-APPLY.patch') {
    git apply --whitespace=nowarn 'docs\cards\CARD-315-APPLY.patch'
  }
}
git add CHANGELOG.md docs/cards/CARD-315-education-continuity-honesty.md docs/cards/CARD-315-APPLY.patch docs/cards/CARD-315-APPLY.ps1 src/web/static/modules/studios/education.js src/web/templates/index.html tests/unit/frontend/education_continuity_315.test.js tests/unit/frontend/factory_popup_scroll_314.test.js tests/unit/frontend/observe_expand_scroll_312.test.js tests/unit/frontend/settings_collapse_migrate_313.test.js
git restore --staged uv.lock 2>$null
git status -sb
if (git diff --cached --quiet) { Write-Host 'nothing to commit (already applied?)' } else {
  git commit -m "fix(education): CARD-315 continuity collapse scroll + origin HITL"
  git push origin feat/super-marathon-ui
}
Write-Host "tip=$(git rev-parse --short HEAD)"
netstat -ano | Select-String ':8000\s' | ForEach-Object {
  if ($_ -match '\s+(\d+)\s*$') {
    $procId = $Matches[1]
    if ($procId -and $procId -ne '0') { taskkill /F /PID $procId 2>$null }
  }
}
python scripts/restart_serve.py --port 8000
Start-Sleep -Seconds 2
$html = (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/).Content
@('CARD-315: Education sections collapse + scroll','edu-section','data-edu-section="quiz"','app.js?v=2.0.51') | ForEach-Object {
  if ($html -notmatch [regex]::Escape($_)) { Write-Warning "MISSING in HTML: $_" } else { Write-Host "OK HTML: $_" }
}
Write-Host 'Ctrl+F5 Education: collapsed panels; expand+scroll; Ask keeps journey/HITL on Education session; rail stays'
