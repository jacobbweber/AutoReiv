# CARD-320 apply on Jarvis (D:\Projects\Active\AutoReiv)
# Run from repo root on feat/education-studio-finish after fetch.
$ErrorActionPreference = "Stop"
Set-Location "D:\Projects\Active\AutoReiv"
git fetch origin feat/education-studio-finish
git checkout feat/education-studio-finish
# If remote tip still has PLACEHOLDER course.py, restore from this bundle next to script:
$bundle = Join-Path $PSScriptRoot "CARD320_bundle.tgz"
if (Test-Path $bundle) {
  tar -xzf $bundle
  Write-Host "Restored CARD-320 files from bundle"
}
git add src/application/education/course.py `
  src/infrastructure/memory/repositories/education_course_ops.py `
  src/infrastructure/memory/repositories/agent_memory.py `
  tests/unit/education/test_card320_course_mastery_model.py `
  docs/cards/CARD-320-education-course-mastery-model.md `
  docs/cards/CARD-320-CHANGELOG-SNIPPET.md `
  src/web/routers/education.py `
  src/web/static/modules/studios/education.js `
  src/web/templates/index.html `
  CHANGELOG.md
# Leave uv.lock dirty
git status -sb
git commit -m "feat(education): CARD-320 course + mastery model in memory.db"
git push origin feat/education-studio-finish
python scripts/restart_serve.py --port 8000
