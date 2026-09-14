# CARD-318 CHANGELOG snippet (fold into CHANGELOG.md [Unreleased])

Insert under `## [Unreleased]` (keep existing CARD-317/316 notes):

```md
### Added
- CARD-318: Education Retrieval binary external grade prove-and-harden — Priming-seeded (or upsert) practice → `grade_answer_binary` / `grader: binary_external` → durable item×mastery pass/fail in memory.db; miss sets `next_due` stage0=+1d (1-3-7-30); quiz selection prefers Priming unseen; empty expected_answer → 422; restart-safe TDD (`tests/unit/education/test_card318_retrieval_binary_grade.py`)
```

Jarvis fold:
```
cd D:\Projects\Active\AutoReiv
git fetch origin feat/education-retrieval-318
git checkout feat/education-retrieval-318
git pull --ff-only origin feat/education-retrieval-318
# If tip CHANGELOG lacks CARD-318 Unreleased line, insert snippet above then:
# git add CHANGELOG.md && git commit -m "docs(changelog): fold CARD-318 Unreleased note" && git push
```
