# CARD-316 — restore CHANGELOG.md (required)

An MCP size-limit push accidentally truncated `CHANGELOG.md` on `feat/education-learning-os` tip.
Product code + TDD for CARD-316 are fine; only the changelog blob needs restore.

## On Jarvis (`D:\\Projects\\Active\\AutoReiv`)

```powershell
cd D:\Projects\Active\AutoReiv
git fetch origin feat/education-learning-os
git checkout feat/education-learning-os
git pull --ff-only origin feat/education-learning-os
# Restore full history from last good blob (pre-truncate):
git show 45149d5:CHANGELOG.md | Set-Content -Encoding utf8 CHANGELOG.md
# Fold CARD-316 Unreleased bullet (also in docs/cards/CARD-316-CHANGELOG-SNIPPET.md):
$snip = @"
### Fixed
- CARD-316: Education learner ledger prove-and-harden — `record_education_grade` no longer swallows learner-fact sync; TDD pins for memory.db path, miss→1-3-7-30 `next_due`, binary external grade, restart-safe reopen + weakness facts (`tests/unit/education/test_card316_learner_ledger.py`)

"@
$cl = Get-Content -Raw CHANGELOG.md
if ($cl -notmatch 'CARD-316:') {
  $cl = $cl -replace '## \[Unreleased\]\r?\n\r?\n', "## [Unreleased]`n`n$snip"
  Set-Content -Encoding utf8 CHANGELOG.md -Value $cl
}
git add CHANGELOG.md
git commit -m "docs(changelog): restore full CHANGELOG + CARD-316 Unreleased note"
git push origin feat/education-learning-os
```

Leave `uv.lock` uncommitted.
