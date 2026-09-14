## [Unreleased]

### Fixed
- CARD-316: Education learner ledger prove-and-harden — `record_education_grade` no longer swallows learner-fact sync; TDD pins for memory.db path, miss→1-3-7-30 `next_due`, binary external grade, restart-safe reopen + weakness facts (`tests/unit/education/test_card316_learner_ledger.py`)

### Added
- CARD-313: Settings collapsed sections (Providers / Data / Preferences / Connections) + honest `POST /api/data-dir/migrate` (copy, validate, `*_backup_<ts>`, persist `AUTOREIV_DATA_DIR`)

### Fixed
- CARD-314:
- CARD-315: Education Learning OS panels collapsed on load (`details.edu-section`); expand scrolls; Ask keeps journey/HITL on origin Education session Train Specialist modal scrolls (max-h + body overflow); Factory studio min-h-0 + full desktop window (not toast); Agents deep-link still scopes agent scope
- CARD-312: Observe expand sections scroll with the studio panel (phone + desktop)


- CARD-311: Observe collapsible sections + agent KPI select from real `/api/observability/kpi`; journey chips from traces; serve `0.0.0.0 --reload`


### Added
- CARD-310: Routines structured schedule (schedule_rule) + full agent pickers

PLACEHOLDER_SEE_SNIPPET_FILE
