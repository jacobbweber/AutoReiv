---
id: CARD-722
title: "Docker In-App Software Updates and Editable Default Origin URL"
type: feature
status: Done
priority: P1
milestone: M31
needs_decision: none
proof:
  journeys: [card-722-docker-in-app-software-updates-and]
  checks: [tests/unit/system/test_card722_docker_updates_and_origin.py]
branch: feat/card-722-docker-in-app-software-updates-and
log: {minutes: 25, qa_runs: 1, findings: 0}
created: 2026-10-18
---

# CARD-722 Docker In-App Software Updates and Editable Default Origin URL

## Intent
Today, **Settings -> Preferences -> System & Software Updates** disables **Update now** and branch switching whenever `deployment_mode == "docker"`, and leaves **Origin URL** empty/read-only when `/app` in the container has no `.git` folder. Jacob wants Docker deployments to check for updates out-of-the-box against the default AutoReiv repository URL (`https://github.com/jacobbweber/AutoReiv.git`), allow users to edit that Origin URL if desired, pick `main` or another branch, and pull + redeploy the container from the UI.

## Goal
1. **Default + Editable Origin URL**: `#updateRemoteUrl` defaults to `https://github.com/jacobbweber/AutoReiv.git` automatically (never blank), and operators can edit and save a custom Origin URL at any time in **Settings -> Preferences -> System & Software Updates**.
2. **Always-On Update Check & Branch Selection**: Both Git clones and Docker deployments can click **Check for Updates**, view commits behind on `main` (or any selected branch such as `qa`), switch branches, and click **Update now** (or enable daily auto-update) to pull the latest commit and restart/redeploy the server.

## Change
- `src/domain/system/models.py`:
  - Add `DEFAULT_ORIGIN_URL = "https://github.com/jacobbweber/AutoReiv.git"`.
  - Restore `upstream_repo_url: Optional[str] = Field(default=DEFAULT_ORIGIN_URL)` and `tracked_branch: Optional[str] = Field(default=None)` on `UpdateConfig` and default `SystemVersionInfo.remote_url` to `DEFAULT_ORIGIN_URL`.
- `src/application/system/update_git_ops.py` & `src/application/system/update_service.py`:
  - Validate and sync `origin` remote URL (`_validate_origin_url()`, `_set_git_origin_url()`) when saved in `save_update_config()`, rejecting unsafe/argument-injection URLs and resetting empty values to `DEFAULT_ORIGIN_URL`.
  - Support optional `target_branch` on `apply_update(trigger="manual", target_branch=...)` so selecting a branch and clicking **Update now** switches to that branch (if different) and pulls the latest commit before restarting.
  - Fall back to `pip install --no-cache-dir --no-deps -e .` in `_default_uv_sync()` when running inside a container without `uv`/`.venv`.
- `src/application/system/serve_restarter.py`:
  - In Docker containers (`_is_docker_container()`), `DetachedScriptRestarter.schedule_restart()` spawns a detached 1-second delayed `os.kill(1, signal.SIGTERM)` so the HTTP response finishes and Docker (`restart: unless-stopped`) immediately restarts the container on the updated code.
- `Dockerfile`:
  - Install `git` and `ca-certificates` in the `runner` stage, copy `.git/` into `/app/.git/`, and set `AUTOREIV_SERVE_HOST=0.0.0.0` and `AUTOREIV_SERVE_PORT=8000`.
- `src/web/templates/partials/settings_preferences.html` & `src/web/static/modules/studios/settings/updates.js`:
  - Make `#updateRemoteUrl` editable (pre-filled with `https://github.com/jacobbweber/AutoReiv.git` by default) with `#saveUpdateOriginBtn` (**Save Origin**) and `#resetUpdateOriginBtn` (**Reset**).
  - Enable `#applyUpdateBtn`, `#updateBranchSelect`, and `#switchBranchBtn` for both `git` and `docker` deployment modes.

## What dies
- The restriction in `updates.js` (`const gitOk = data.is_git && data.deployment_mode === 'git'`) that hid/disabled in-app updates and branch switching in Docker mode.
- Read-only restriction on `#updateRemoteUrl` in `src/web/templates/partials/settings_preferences.html`.

## Proof
- Journey `card-722-docker-in-app-software-updates-and`:
  1. Open **Settings -> Preferences -> System & Software Updates**, verify `#updateRemoteUrl` is pre-populated with `https://github.com/jacobbweber/AutoReiv.git` and editable, and verify `#applyUpdateBtn`, `#updateBranchSelect`, and `#switchBranchBtn` are enabled.
  2. Update `#updateRemoteUrl`, save, and verify `/api/system/updates/config` persists `upstream_repo_url` and resets cleanly to the default URL.
  3. Verify branch listing populates and zero horizontal overflow occurs on desktop and phone.
- Checks: `tests/unit/system/test_card722_docker_updates_and_origin.py`.

## Plan and decisions
- **Architecture Decision (`build` approved by Jacob)**:
  - Selected **Option 1**: Self-Updating Git Worktree Inside the Container (`git` in `Dockerfile` + in-place `git fetch/pull/checkout` + container PID 1 restart via `SIGTERM` and `restart: unless-stopped`, without exposing `/var/run/docker.sock`).

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-722-docker-in-app-software-updates-and` | desktop (1440×900) | PASS | Editable `#updateRemoteUrl` pre-populated with `https://github.com/jacobbweber/AutoReiv.git`, Save/Reset Origin persisted via `/api/system/updates/config`, Update now & branch controls enabled, 0px overflow |
| `card-722-docker-in-app-software-updates-and` | phone (390×844) | PASS | Editable `#updateRemoteUrl`, Save/Reset Origin persisted, Update now & branch controls enabled, 0px overflow |

Screenshots:
- `/tmp/autoreiv-qa/card-722/card-722-docker-in-app-software-updates-and-desktop-01-1-open-settings-preferences-system-software-upda.png`
- `/tmp/autoreiv-qa/card-722/card-722-docker-in-app-software-updates-and-desktop-02-2-save-custom-origin-url-verify-api-system-updat.png`
- `/tmp/autoreiv-qa/card-722/card-722-docker-in-app-software-updates-and-phone-01-1-open-settings-preferences-system-software-upda.png`

## Release note
Enabled in-app git updates, branch switching, and container auto-restart for Docker deployments, and made the Origin URL in Settings -> Preferences -> System & Software Updates editable with `https://github.com/jacobbweber/AutoReiv.git` as the default (CARD-722).
