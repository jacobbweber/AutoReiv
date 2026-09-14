# CARD-318 APPLY on Jarvis (when tip has tests but product delta still pending)
$ErrorActionPreference = "Stop"
Set-Location "D:\Projects\Active\AutoReiv"
git fetch origin feat/education-retrieval-318
git checkout feat/education-retrieval-318
git pull --ff-only origin feat/education-retrieval-318
if (Test-Path "docs/cards/CARD-318-APPLY.patch") {
  git apply --whitespace=nowarn "docs/cards/CARD-318-APPLY.patch"
  git add src/application/education/learner_model.py src/web/routers/education.py
  git status -sb
  Write-Host "Review then: git commit -m \"feat(education): CARD-318 prefer Priming unseen + harden grade\" ; git push"
} else {
  Write-Host "No APPLY.patch on tip — product may already be folded."
}
# Fold CHANGELOG snippet if missing
$cl = Get-Content CHANGELOG.md -Raw
if ($cl -notmatch "CARD-318: Education Retrieval") {
  $snip = Get-Content "docs/cards/CARD-318-CHANGELOG-SNIPPET.md" -Raw
  Write-Host "CHANGELOG missing CARD-318 — fold docs/cards/CARD-318-CHANGELOG-SNIPPET.md under [Unreleased]"
}
