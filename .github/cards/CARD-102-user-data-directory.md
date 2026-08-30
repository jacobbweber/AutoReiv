# [CARD-102] User data directory (migrate live data/autoreiv.db + wiki into it, env default, no wipe)

> **Status**: Ready
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/control-plane-data-dir/`
> **Labels**: `type:feature`, `area:data`, `area:infra`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---

## 1. Why / Intent
Live user state must leave the git checkout (Hermes `~/.hermes` pattern). One `AUTOREIV_DATA_DIR` holds the db (jobs, custom agents, settings), wiki, user skill packs, and future packs. Repo seeds builtins. Existing `./data/autoreiv.db` and `./data/wiki` copy in. No wipe.

## 2. What to Build
- Resolve `AUTOREIV_DATA_DIR`: env > setting > platform default (`%LOCALAPPDATA%\AutoReiv`, `~/.autoreiv`, Docker `/data`).
- Layout: `autoreiv.db`, `wiki/`, `skills/`, reserved `agents/` and `templates/jobs/`.
- Derive db/wiki unless `AUTOREIV_DB_PATH` / `AUTOREIV_WIKI_PATH` are explicit.
- First-boot copy migrate from today's live `./data` paths. Copy, not move. Do not overwrite dest. Do not delete source.
- Wire `app.py`, CLI `--data-dir`, `.env.example`, docker-compose one volume.

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-DATA-001]`: Env > setting > platform default outside the checkout.
- [ ] `[REQ-DATA-002]`: Live db, wiki, and skills resolve under the data dir.
- [ ] `[REQ-DATA-003]`: Derived db/wiki paths; explicit env overrides win.
- [ ] `[REQ-DATA-004]`: Copy migrate live `./data/autoreiv.db` + `./data/wiki`. No wipe. No dest overwrite.
- [ ] `[REQ-DATA-005]`: User writes land in the data dir. Repo seeds builtins only.
- [ ] `[REQ-DATA-006]`: Docker is one volume at `AUTOREIV_DATA_DIR=/data`.
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- No kernel changes. No Agent Builder. No SkillOpt. No LangGraph.
- Spec: `docs/specs/control-plane-data-dir/`.

