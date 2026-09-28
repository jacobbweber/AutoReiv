---
id: CARD-451
title: "Settings software updates via git (fetch, ff-only pull, branch switch, daily auto-update)"
status: Done
created: 2026-09-24
completed: 2026-09-24
branch: feat/card-451-settings-software-updates
related:
  - CARD-196
  - CARD-452
  - CARD-453
labels:
  - type:feature
  - area:settings
  - area:system
  - P2
---

# [CARD-451] Settings software updates via git (fetch, ff-only pull, branch switch, daily auto-update)

> **Status**: Done
> **Completed**: 2026-09-24 — live-tested by Jacob on Jarvis (Settings System & Software Updates; no-upstream honesty + timestamps + branch picker)
> **Created**: 2026-09-24
> **Branch**: `feat/card-451-settings-software-updates`
> **Observed during**: Jacob request after CARD-449 merge - revisit Settings System & Software Updates; add Update now / git pull, branch fetch/switch, preferences, optional daily auto-pull
> **Related**: CARD-196 (original System & Software Updates surface, REQ-UPD-001..005)
> **ADR references**: [ADR-0005](../adr/0005-autonomous-routine-engine-and-async-background-scheduler.md) (RoutineScheduler); no dedicated software-update ADR found - prefer extending CARD-196 service rather than inventing a second update stack
> **Labels**: `type:feature`, `area:settings`, `area:system`, `P2`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine open questions, safety rules, or Settings copy - **still no product code** |
| **`build`** | Implement the git-based update controls, preferences, and daily auto-update on top of the existing CARD-196 surface |
| **`merge to qa`** | After live proof on Jarvis that Check / Update now / branch switch / preferences behave as specified (and auto-update stays OFF by default) |

Do not write product code until Jacob says **build** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards / systems |
|----------|-----------------|
| **Depends on** | Existing CARD-196 surface: `#settingsSystemUpdatesCard` in `src/web/templates/index.html`, `src/web/static/modules/studios/settings.js`, `src/web/routers/system.py`, `src/application/system/update_service.py`, `src/domain/system/models.py` |
| **Depends on** | Restart path: `scripts/restart_serve.ps1` (wraps `scripts/restart_serve.py`) with host binding preserved (`0.0.0.0:8000` on Jarvis) |
| **Depends on** | Scheduler choice: [ADR-0005](../adr/0005-autonomous-routine-engine-and-async-background-scheduler.md) `RoutineScheduler` (`src/application/routines/scheduler.py`) and/or cadence pattern from `DataDirBackupScheduler` (`src/application/system/backup_scheduler.py`, CARD-404) |
| **Blocked by** | Nothing for scaffolding; **build** should land after open questions below are answered (or defaults explicitly accepted) |
| **Unlocks** | Operators can fetch/ff-pull/switch branches from Settings without a shell, with durable preferences and a visible update history |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. Revisit software updates in Settings. Add a clear **Update** path that uses git to get the latest changes - including fetching and switching/pulling branches.
2. Put update preferences in Settings (not a separate app outside Settings).
3. Optionally support a **daily auto-pull** (default OFF) that obeys the same safety rules as manual Update now.
4. Never destroy local work: no reset, no force, no automatic stash, no discarding local commits. Fast-forward only.
5. After a successful update or branch switch: dependency check, then restart serve while preserving the Jarvis host binding (`0.0.0.0:8000`).
6. Security: local operator only; fixed command set; endpoints must not accept arbitrary git args or remote URLs from the client.
7. Out of scope: release tagging, version bump automation, pushing to remotes.

### Beat 2: What AutoReiv does now

1. **UI**: Settings Studio Preferences hosts **System & Software Updates** as `#settingsSystemUpdatesCard` in `src/web/templates/index.html` (comment marks CARD-196 / REQ-UPD-001..005). It shows version pill, deployment badge, commit short SHA, branch name, working-tree Clean/Dirty, platform/Python. Upstream section has free-text **Repository URL** and **Tracked Branch**, **Save Repository Settings**, **Check for Updates**, and (when clean git + update available) **Apply Update (Fast-Forward)**. Docker mode shows a manual `docker compose pull && docker compose up -d` helper.
2. **Frontend wiring**: `src/web/static/modules/studios/settings.js` (System & Software Updates block ~L1499) loads version + config on Settings open; Check calls `GET /api/system/updates/check?branch=...`; Apply calls `POST /api/system/updates/apply`; Save calls `PUT /api/system/updates/config`.
3. **API** (`src/web/routers/system.py`):
   - `GET /api/system/version` -> `SystemVersionInfo` (version, short commit, branch, is_git, is_dirty, deployment_mode, python, platform)
   - `GET /api/system/updates/config` / `PUT /api/system/updates/config` -> `UpdateConfig` stored as setting key `system_update_config` in user-data SQLite via `SQLiteStateStore`
   - `GET /api/system/updates/check` (optional `branch` query) -> `UpdateCheckResult`
   - `POST /api/system/updates/apply` -> `UpdateApplyResult`
4. **Service** (`src/application/system/update_service.py`):
   - **Check** prefers GitHub REST `repos/{owner}/{repo}/commits/{tracked_branch}` (+ compare for `commits_behind`); falls back to `git ls-remote <upstream_url> refs/heads/<branch>`. It does **not** run `git fetch --prune origin`.
   - **Apply** refuses non-git deployment modes and dirty trees; snapshots user-data SQLite (`data_dir/database/autoreiv.db` or `autoreiv.db`, or `AUTOREIV_DB_PATH`); then runs `git pull --ff-only <upstream_repo_url> <tracked_branch>`, with fallback `git pull --ff-only`. Success message says restart is recommended; **no in-app restart** is triggered.
5. **Config model gaps**: `UpdateConfig.auto_check_cadence` exists (`manual` / `startup` / `daily`, default `manual`) in `src/domain/system/models.py` but is **not** exposed in the Settings UI and is **not** acted on by any scheduler tick.
6. **Missing vs desired**: no HEAD subject line; no upstream tracking name; no local ahead/behind vs current branch upstream; no last-fetch timestamp; no branch picker or checkout/switch; no refuse path for "local ahead / diverged" beyond raw ff-only failure text; no git-in-progress guard; no dependency/requirements change detection; no update history log; no daily auto-pull runner; Apply currently accepts a configurable **remote URL** from Settings (broader than the fixed-command security rule in Beat 3).
7. **Scheduler exists**: `RoutineScheduler` in `src/application/routines/scheduler.py` (seeded/started from `src/web/app.py`, ADR-0005). Separate `DataDirBackupScheduler` in `src/application/system/backup_scheduler.py` shows a cadence-in-settings pattern (CARD-404). Chat tracks active streams in `_active_stream_tasks` (`src/web/routers/chat.py`) - useful for "defer while agent job running".
8. **Restart path**: `scripts/restart_serve.ps1` (CARD-256 wrapper) calls `uv run python scripts/restart_serve.py --port ... --host ...`. Jarvis operators use `-HostAddr 0.0.0.0 -Port 8000`.

### Beat 3: What will change

1. **Status panel** on `#settingsSystemUpdatesCard` shows: current branch; HEAD short SHA + subject; upstream tracking ref; ahead/behind counts; working tree clean/dirty; last fetch time.
2. **Check for updates** becomes `git fetch --prune origin` (fixed remote name `origin`), then refreshes ahead/behind vs upstream. No arbitrary remote URL from the client.
3. **Update now** = fast-forward-only pull of the **current** branch from its upstream. Refuse with a clear message if: working tree dirty; branch diverged or local ahead (never reset, never force, never stash automatically, never discard local commits); or a git operation is already in progress.
4. **Branch picker** lists local + remote-tracking branches. Switching requires a clean tree; for remote-only branches create a local tracking branch; after switch, same ff-only rules apply for Update now.
5. **After successful update or switch**: dependency check (if `requirements.txt` / `pyproject.toml` / lockfiles changed vs previous HEAD - warn and/or run install per existing repo tooling; decision recorded under Open questions); then restart serve via existing restart path (`scripts/restart_serve.ps1` or in-app equivalent) preserving host binding (`0.0.0.0:8000` on Jarvis); show the result in Settings.
6. **Daily auto-update** preference, default **OFF**, with time-of-day. Same safety rules as Update now. Prefer existing scheduler/routine mechanism (`RoutineScheduler` / backup-scheduler cadence pattern). Record last run result visible in Settings. **Never** run mid active agent job - defer if jobs/streams are running (requirement).
7. **Durable state** in user-data settings (`storage.db` / `SQLiteStateStore`): update preferences; update history log entries with timestamp, result, from-SHA -> to-SHA.
8. **Failure modes** (clear operator messages): git not on PATH; checkout is not a git repo / packaged-standalone/docker mode (hide Update now or show unsupported, keep version inspection); network failure; auth failure; ff-only refusal (merge conflicts impossible by design); restart failure.
9. **Security**: local operator only; endpoints accept only a fixed command set (fetch/prune origin, ff-only pull of current upstream, list branches, checkout/track known refs). Do **not** accept arbitrary git args or remote URLs from the request body. Tighten or remove the free-text upstream URL field as part of this card (see Open questions).
10. **Out of scope**: release tagging, version bump automation, `git push`, merging divergent branches in-app.

### Beat 4: What dies today

1. Check-for-updates that only hits GitHub HTTP / `ls-remote` without refreshing local remote-tracking refs via `git fetch`.
2. Apply update that pulls a free-text configured URL/branch instead of ff-only on the current branch upstream with fixed `origin`.
3. Silent absence of daily auto-update despite `auto_check_cadence` existing on the model.
4. "Restart recommended" only - after a successful update/switch the operator should get an explicit restart path that preserves Jarvis bind address.
5. No durable update history or last-run visibility for auto-update.

---

## 2. Acceptance criteria (EARS)

- **[REQ-451-001]** WHEN Settings opens System & Software Updates on a git checkout, THE SYSTEM SHALL display current branch, HEAD short SHA and subject, upstream tracking ref, ahead/behind counts, working-tree clean/dirty, and last fetch time.
- **[REQ-451-002]** WHEN the operator clicks **Check for updates**, THE SYSTEM SHALL run a fixed `git fetch --prune origin` (no client-supplied remote URL or extra args) and refresh ahead/behind against the current branch upstream.
- **[REQ-451-003]** WHEN the operator clicks **Update now** and the working tree is clean, the branch is not ahead/diverged from upstream, and no git operation is in progress, THE SYSTEM SHALL fast-forward-only pull the current branch from its upstream and record from-SHA -> to-SHA in the update history.
- **[REQ-451-004]** WHEN **Update now** is requested and the working tree is dirty, OR the branch has diverged / is ahead of upstream, OR a git operation is in progress, THE SYSTEM SHALL refuse with a clear message and SHALL NOT reset, force, stash automatically, or discard local commits.
- **[REQ-451-005]** WHEN the operator selects a branch in the branch picker, THE SYSTEM SHALL require a clean working tree; WHERE the branch exists only on the remote, THE SYSTEM SHALL create a local tracking branch; THE SYSTEM SHALL then apply the same ff-only update rules afterward.
- **[REQ-451-006]** WHEN an update or branch switch succeeds, THE SYSTEM SHALL perform the agreed dependency check (warn and/or install per Open question resolution), restart serve using the existing restart path while preserving the configured host binding (on Jarvis: `0.0.0.0:8000`), and show the outcome in Settings.
- **[REQ-451-007]** THE SYSTEM SHALL expose a daily auto-update preference defaulting to OFF with a time-of-day; WHERE enabled, THE SYSTEM SHALL use the same safety rules as Update now, record last-run result in Settings, and SHALL defer the run while active agent jobs/streams are in progress.
- **[REQ-451-008]** THE SYSTEM SHALL persist update preferences and an update history log (timestamp, result, from-SHA -> to-SHA) in user-data settings storage (`storage.db` / `SQLiteStateStore`), never in the git checkout.
- **[REQ-451-009]** WHEN git is missing from PATH, OR the deployment is not a git checkout (standalone/docker/packaged), THE SYSTEM SHALL hide or clearly mark Update now / branch switch as unsupported while still showing version inspection where available.
- **[REQ-451-010]** THE update/check/switch endpoints SHALL accept only a fixed command set and SHALL NOT accept arbitrary git arguments or remote URLs from the client.
- **[REQ-451-011]** Out of scope for this card: release tagging, version bump automation, and pushing to remotes.

---

## 3. Implementation map (proposed)

| Area | Path / notes |
|------|----------------|
| UI card | `src/web/templates/index.html` `#settingsSystemUpdatesCard` |
| Settings JS | `src/web/static/modules/studios/settings.js` System & Software Updates block |
| API | `src/web/routers/system.py` (extend/replace CARD-196 update routes; keep version route) |
| Service | `src/application/system/update_service.py` (git fetch/ff-only/branch switch; drop arbitrary URL pull) |
| Models | `src/domain/system/models.py` (`UpdateConfig`, status/history models) |
| Preferences / history | `SQLiteStateStore` settings keys under user data (e.g. extend `system_update_config`, add history list) |
| Scheduler | `src/application/routines/scheduler.py` (ADR-0005) and/or cadence worker patterned on `src/application/system/backup_scheduler.py` |
| Active-job defer | `src/web/routers/chat.py` `_active_stream_tasks` (and any routine RUNNING state) |
| Restart | `scripts/restart_serve.ps1` / `scripts/restart_serve.py` |
| Tests | New unit tests under `tests/unit/` (temp git repo fixtures; negative: dirty, ahead, in-progress, non-git) |

---

## 4. Proof / live-test notes

0. **No upstream honesty**: on an unpushed feat branch, Ahead/Behind shows `No upstream`; Check banner warns (not "Up to date"); Update now disabled with reason. Timestamps local with ISO tooltip. No `CARD-` in user copy. Branch picker lists `qa`/`main`/remotes.

1. On Jarvis git checkout at `D:\Projects\Active\AutoReiv`, open Settings -> System & Software Updates: confirm status panel fields (branch, SHA+subject, upstream, ahead/behind, dirty, last fetch).
2. **Check for updates**: fetch runs; ahead/behind updates; no remote URL field required for the check.
3. Clean tree behind upstream: **Update now** ff-only succeeds; history shows from->to; serve restarts and still listens on `0.0.0.0:8000`.
4. Negative: dirty tree refuses; local-ahead/diverged refuses without reset/stash; non-git/docker path shows unsupported.
5. Branch picker: switch to a remote-only branch creates tracking branch on clean tree; dirty tree refuses switch.
6. Daily auto-update left **OFF** on live data unless Jacob explicitly enables it; if enabled in a controlled test, confirm defer while a chat stream/agent job is active and last-run result appears in Settings.

---

## 5. Constraints

- This card is **docs-only** until Jacob says **build**. Status remains **Ready**.
- Never reset `qa`, never force-push, never auto-stash, never discard local commits.
- Do not merge to `main`; no version bump; no release tag for this work.
- Do not invent a second Settings update screen outside `#settingsSystemUpdatesCard`.
- Endpoints must not shell out with operator-supplied argv or remote URLs.
- User data stays under AppData / `AUTOREIV_DATA_DIR` - never write preferences/history into the checkout.

---

## 6. Decisions (Jacob answers locked 2026-09-24)

Open questions closed before **build**. Recorded as decisions + EARS below.

1. **Restart policy**: Restart automatically after a successful manual **Update now** or **branch switch**. Daily auto-update restarts only when idle (nothing busy).
2. **Daily auto-update branch**: Applies to whatever branch is currently checked out (any branch).
3. **Dependencies**: Detect when dependency files changed (`pyproject.toml`, `uv.lock`, `requirements*.txt`). Install automatically via `uv sync`. If install fails: stop, surface the error, do **not** restart into a broken state.
4. **Remote URL**: Remove free-text upstream URL input. Remote is fixed `origin`, shown read-only (`git remote get-url origin`).
5. **Busy definition**: Active chat streams (`_active_stream_tasks` in `src/web/routers/chat.py`), running routines (`RoutineStatus.RUNNING` via routine runs / last_status), and running Studio / training / Factory jobs (`jobs` + Factory packet jobs in `queued`/`running`/`waiting_approval`).
6. **Update now target**: Pulls the **current branch's upstream**. Drop the separate tracked-branch setting; the branch picker replaces it.

### Locked EARS (decisions)

- **[REQ-451-012]** WHEN a manual Update now or branch switch succeeds (and dependency install succeeds or was not needed), THE SYSTEM SHALL restart serve automatically while preserving the current host/port binding.
- **[REQ-451-013]** WHEN daily auto-update is due and the system is busy per REQ-451-015, THE SYSTEM SHALL defer the entire auto-update (fetch/pull/restart) and retry later until idle or a bounded retry limit; WHEN it runs while idle and succeeds, THE SYSTEM SHALL restart serve automatically.
- **[REQ-451-014]** WHEN dependency files change across an update or switch, THE SYSTEM SHALL run `uv sync` automatically; WHEN install fails, THE SYSTEM SHALL refuse restart and surface the error.
- **[REQ-451-015]** WHILE any chat stream task is active, OR any routine run/last_status is RUNNING, OR any Studio/Factory job is queued/running/waiting_approval, THE SYSTEM SHALL treat the instance as busy for daily auto-update and defer.
- **[REQ-451-016]** THE SYSTEM SHALL use fixed remote name `origin` only; THE SYSTEM SHALL NOT accept client-supplied remote URLs; THE SYSTEM SHALL show `origin` URL read-only in Settings.
- **[REQ-451-017]** WHEN Update now is requested, THE SYSTEM SHALL fast-forward the currently checked-out branch from its upstream; THE SYSTEM SHALL NOT use a separate tracked-branch setting.

### Live-test defect fixes (2026-09-24)

- **[REQ-451-018]** WHEN the current branch has no upstream tracking ref, THE SYSTEM SHALL return `ahead`/`behind` (and check `commits_ahead`/`commits_behind`) as null (not 0), surface **No upstream** in the status grid (not `+0 / -0`), and after **Check for updates** show a neutral/warning banner that the branch has no upstream to compare against (never claim up to date). THE SYSTEM SHALL disable **Update now** with a visible reason while no upstream is configured.
- **[REQ-451-019]** WHEN rendering Last fetch or Update history timestamps in Settings, THE SYSTEM SHALL show the browser's local time in a readable format and keep the full ISO string in a title/tooltip.
- **[REQ-451-020]** THE System & Software Updates card SHALL NOT show internal card IDs (e.g. `CARD-451`) in operator-visible copy.
- **[REQ-451-021]** WHEN the branch picker loads, THE SYSTEM SHALL list local and remote-tracking branches from `origin` (including `qa` and `main` when present), not only the current branch.


---

## 7. Reply phrases

- After Jarvis live proof: say **merge to qa**.
