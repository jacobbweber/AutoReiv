# [CARD-272] Foundation audit - Install / Compose / update truth

> **Status**: Done
> **Created**: 2026-09-12
> **Spec Reference**: Foundation audit after CARD-271. Architect: install / Compose / update must be real (version, compose volumes, install scripts, honest apply refuse). Stack on eat/react-job-spine-truth-271 @ c8990b. Hold FF until Jacob merge phrase.
> **Labels**: 	ype:chore, P0, FoundationAudit, Deploy, AntiTheatre
> **Branch**: eat/install-compose-update-truth-272 (off 271 tip; push feat only)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Install, Docker Compose, and in-app Update are not costume: Settings shows a real version/commit; Compose persists data; Windows/systemd installers exist; Apply refuses dirty/non-git honestly.
2. Do **not** run a live pply_update pull on Jarvis in this card.
3. **Not this card**: UI marathon, Lumina, rewrite of CARD-196/193.

### Beat 2: What AutoReiv Does Now
1. UpdateService + /api/system/version|updates/check|updates/apply + Settings fetches (CARD-196).
2. docker-compose.yml named volume utoreiv-data + AUTOREIV_DATA_DIR=/data.
3. deploy/windows/install_windows_service.ps1 + deploy/systemd/install_systemd.sh.
4. Missing: a single foundation-audit live proof artifact that these three still hold on the current feat stack.

### Beat 3: What Will Change
1. Lock-file tests: compose data volume + env; install scripts present; Settings wires version/check.
2. Live smoke: GET /api/system/version commit matches git rev-parse --short HEAD; check endpoint responds; no apply.
3. CHANGELOG; push feat; hold FF.

## 2. Acceptance Criteria

- [x] **[REQ-FAUD-272-001]**: Compose has AUTOREIV_DATA_DIR and a persistent volume for /data.
- [x] **[REQ-FAUD-272-002]**: Windows + systemd install scripts exist under deploy/.
- [x] **[REQ-FAUD-272-003]**: Live /api/system/version is git-real (commit matches checkout); Settings JS calls version + check.
- [x] **[REQ-FAUD-272-004]**: Tests + live artifact 
otes/marathon-card272-live-smoke.json; no live apply; push feat only; hold FF.

## 3. Constraints

- Do not git pull / apply update on Jarvis. Do not docker compose up unless already running.
- Out of scope: UI marathon, horizon D.

## 4. Modules Likely Touched

- docker-compose.yml, deploy/** (read/lock only unless theatre)
- src/web/static/modules/studios/settings.js (only if dead chrome)
- 	ests/unit/system/test_card272_*.py
- 
otes/scripts/install_compose_update_truth_272.py
- CHANGELOG.md

## 5. Design-room one-liner

Install / Compose / update truth: real version, persisted compose data, real installers, honest apply refuse — no live pull.

## 6. Build lock

CoS keep-rolling / Architect 272 bar: Builder may implement immediately on this Ready card.
