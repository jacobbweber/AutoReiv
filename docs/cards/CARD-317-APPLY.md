# CARD-317 apply on Jarvis

```powershell
cd D:\\Projects\\Active\\AutoReiv
git fetch origin feat/education-priming-writeback
git checkout feat/education-priming-writeback
git pull --ff-only origin feat/education-priming-writeback
```

## Mount the writeback API (2 lines in `src/web/app.py`)

After `from src.web.routers.education import router as education_router` add:

```python
from src.web.routers.education_priming import router as education_priming_router
```

After `app.include_router(education_router)` add:

```python
    app.include_router(education_priming_router)
```

## CHANGELOG

Fold `docs/cards/CARD-317-CHANGELOG-SNIPPET.md` into `CHANGELOG.md` [Unreleased] ### Added. Do not replace the whole changelog.

## Smoke

```powershell
python scripts/restart_serve.py --port 8000
```

POST `/api/education/priming/writeback` body:
`{"agent_id":"assistant","topic":"CARD317 Soft Fail Smoke","attempt_forbidden_tools":["wiki_overview"]}`

Then GET `/api/education/mastery?agent_id=assistant` and `/api/education/learner?agent_id=assistant`.
Restart serve; same topic still present. Ctrl+F5. No new Education chrome.
