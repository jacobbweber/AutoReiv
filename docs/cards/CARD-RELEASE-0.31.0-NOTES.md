# v0.31.0 release notes fold-in

House-style CHANGELOG seal (same as v0.30.0): under `## [Unreleased]` insert:

```
## [0.31.0] - 2026-09-14

Learning OS prove-and-harden (CARD-316–319) + Education Studio continuity + UI marathon already on qa.
```

Existing Unreleased bullets (CARD-319…295 / UI marathon) become the 0.31.0 body.

## Version sites bumped on main
- pyproject.toml → 0.31.0
- package.json → 0.31.0
- src/web/routers/system.py health fallback → 0.31.0
- src/application/system/update_service.py fallback → 0.31.0
- src/web/app.py FastAPI `version=` — **still 0.30.0** if this note lands before that bump; fold on Jarvis if needed

## Tag
Create annotated tag on release tip:
`git tag -a v0.31.0 -m "v0.31.0 Learning OS 316–319 + UI marathon" && git push origin v0.31.0`
