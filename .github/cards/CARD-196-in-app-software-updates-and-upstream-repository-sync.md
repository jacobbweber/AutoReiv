# [CARD-196] In-App Software Updates and Upstream Repository Sync

> **Status**: Ready
> **Created**: 2026-09-09
> **Spec Reference**: none
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Three Beats

### Beat 1: What you mean
Most modern desktop and self-hosted applications provide a built-in way to check for updates, inspect release notes, and keep the application current without having to manually monitor git repositories or run terminal commands.

You want AutoReiv to feature an **In-App Update System**:
1. **Version Visibility**: Surface the currently installed version (e.g. `v0.23.0`), active commit hash, and build date clearly in the UI.
2. **Upstream Checking**: Allow operators to check whether a newer version or commit is available on upstream GitHub (e.g. `main` or release tags).
3. **Changeable Repository Source**: Make the upstream repository URL and tracked branch configurable in Settings (defaulting to `https://github.com/jacobbweber/AutoReiv`), so operators who fork, customize, or maintain private mirrors of AutoReiv can point update checks to their own fork or branch.
4. **Release Notes & Change Preview**: Display what has changed (release notes, changelog summary, or commit list) before applying any update.
5. **Safe Upgrade Path**: Research and design safe execution models that protect local SQLite databases (`autoreiv.db`, `packs/*/`), credentials, and user files from being overwritten or corrupted during an update.

---

### Beat 2: What AutoReiv does now
1. **Static Version Definition**:
   - Version is hardcoded in `pyproject.toml` (`0.23.0`) and `package.json` (`0.23.0`).
   - The top navigation bar displays active LLM model badges and token counters, but there is no version indicator or update status pill.
2. **Settings Studio Today (`#view-settings`)**:
   - Provides configuration tabs for LLM Providers, Model Defaults, Prompts, Credential Vault, and Remote Hosts.
   - There is no "System & Updates" or "About AutoReiv" card or tab.
3. **Manual Upgrades Only**:
   - Updating AutoReiv requires the operator to manually drop to the command line, run `git fetch` and `git pull`, reinstall any modified dependencies (`uv sync` or `npm install`), and restart the service or process.
   - Operators have no automated notification when new features or bug fixes land upstream.

---

### Beat 3: What will change (Proposed Architecture)

#### 1. Settings Studio "System & Updates" Surface (`#view-settings`)
- Add a dedicated **System & Updates** panel to Settings Studio (or an "About" dialog accessible from the navigation rail).
- **Installed Build Card**:
  - Version pill (e.g. `v0.23.0`).
  - Active git commit SHA (shortened) and branch (`qa` / `main`).
  - Runtime environment badge (e.g. `Git Clone`, `Docker Container`, `Systemd Service`, `Windows Service`).
- **Upstream Sync Configuration**:
  - `Repository URL`: Text field defaulting to `https://github.com/jacobbweber/AutoReiv.git` (editable for forks / private mirrors).
  - `Tracked Branch / Tag Channel`: Dropdown or input (`main`, `qa`, or `Latest Stable Release`).
  - `Check Cadence`: Options for `Manual Only`, `On Startup`, or `Daily`.
- **Update Action & Status Banner**:
  - `[ 🔄 Check for Updates ]` button.
  - Live status pills:
    - 🟢 *AutoReiv is up to date*
    - 🟡 *Update Available: v0.24.0 (3 commits ahead)*
    - 🔴 *Offline / Upstream Unreachable*
  - `[ 📄 View Release Notes ]` button triggering a modal with changelog details.

---

## 2. Technical Architecture & Update Delivery Options

### Option A: GitHub API Check + Copyable Upgrade Guide (Safest Baseline)
- **Mechanism**:
  - AutoReiv queries the GitHub Releases REST API (`GET https://api.github.com/repos/{owner}/{repo}/releases/latest`) or GitHub Commits API (`GET https://api.github.com/repos/{owner}/{repo}/commits/{branch}`).
  - Compares the remote latest tag/commit against the locally installed `vX.Y.Z` or git HEAD.
  - When an update is detected, AutoReiv displays the changelog and provides a **one-click copyable upgrade command** tailored to the operator's runtime environment (e.g. `docker compose pull && docker compose up -d` or `git pull && uv sync`).
- **Pros**: 100% safe, zero risk of service crash or self-overwrite while running, works universally across all OS platforms and container environments.
- **Cons**: Requires the operator to run a single command outside the web browser.

### Option B: In-App Fast-Forward Git Sync (One-Click Update for Git Clones)
- **Mechanism**:
  - Backend executes read-only `git fetch origin` in the background.
  - Compares `HEAD` with `origin/<branch>`.
  - When the operator clicks `[ 🚀 Apply Update ]`:
    1. **Pre-flight Safety Gate**: Confirms `git status --porcelain` is clean. If uncommitted local changes exist, update aborts with a clear warning to protect operator work.
    2. **Database Snapshot**: Creates timestamped snapshot of `autoreiv.db` to `autoreiv.db.bak`.
    3. **Fast-Forward Merge**: Executes `git merge --ff-only origin/<branch>`.
    4. **Dependency Sync**: Automatically runs `uv sync` / `pip install -e .` if `pyproject.toml` changed.
    5. **Graceful Reload**: Signals the Uvicorn ASGI server to restart or triggers process reload.
- **Pros**: True one-click in-app update experience right from the browser.
- **Cons**: Only applicable when AutoReiv is running from a git checkout (not inside immutable Docker image without rebuild). Requires graceful process restart mechanics.

### Option C: Two-Tier Hybrid Architecture (Recommended)
- **Detection Tier**: Universal GitHub API / Git remote checking available in all deployment modes with configurable repository URL and branch.
- **Execution Tier**:
  - If running inside a git checkout with write permissions: provide both the **One-Click Safe Apply** button (Option B) and the manual command.
  - If running in Docker or non-git environment: provide the **Environment-Specific Upgrade Guide** (Option A) with one-click copy.

---

## 3. Proposed REST API Endpoints

1. `GET /api/system/version`:
   - Returns `{ current_version: "0.23.0", commit: "ceb66a7", branch: "qa", is_git: true, is_dirty: false, deployment_mode: "git" }`.
2. `GET /api/system/updates/check`:
   - Queries configured upstream repository.
   - Returns `{ update_available: true, latest_version: "0.24.0", remote_commit: "a1b2c3d", commits_behind: 3, release_notes: "...", release_url: "..." }`.
3. `PUT /api/system/updates/config`:
   - Updates repository URL, branch, and check schedule in SQLite `settings` table.
4. `POST /api/system/updates/apply`:
   - Initiates pre-flight checks, backup, and fast-forward pull (with streaming progress status).

---

## 4. Safety & Invariant Constraints

1. **User Data Isolation**:
   - Updating code must NEVER touch or delete SQLite databases (`autoreiv.db`, `packs/*/*_storage.db`, `packs/*/*_memory.db`), `.env` secrets, or Credential Vault keys.
2. **Dirty Tree Guard**:
   - Never run `git pull` or overwrite local changes if uncommitted modifications exist in the working tree.
3. **Offline Resilience**:
   - If the machine is offline or GitHub rate limits are reached, the system must fail silently with a low-priority indicator without blocking any local features.
4. **Air-Gap / Fork Support**:
   - The repository URL must accept any valid HTTPS or SSH git URL (e.g. internal GitLab, Gitea, GitHub enterprise, or public fork).

---

## 5. Acceptance Criteria (When Scheduled for Implementation)

- [ ] System version, active commit hash, and deployment mode visible in UI.
- [ ] Configurable Upstream Repository URL and Tracked Branch in Settings Studio.
- [ ] Manual "Check for Updates" button returns live upstream comparison.
- [ ] Release notes / changelog preview displayed when an update is available.
- [ ] Safe git fast-forward update pathway with working tree dirty check and database snapshotting.
- [ ] Copyable environment-tailored update commands for Docker and service installations.
- [ ] Hermetic automated unit tests for version resolution, GitHub API parser, and git update runner.
- [ ] Zero lint errors via `ruff` and `eslint`.
