---
id: CARD-731
title: "Docker mounts the projects folder and ships a dev toolchain"
type: feature
status: In Review
priority: P1
milestone: M32
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/deploy/test_card731_docker_projects_and_toolchain.py, docker smoke]
branch: feat/card-731-docker-projects-mount-and-dev-toolchain
log: {minutes: 10, qa_runs: 3, findings: 3}
created: 2026-10-19
---

# CARD-731 Docker mounts the projects folder and ships a dev toolchain

## Intent
ADR-0067 (approved with `build`) makes projects user data: one folder, `AUTOREIV_PROJECTS_DIR`, else `<data root>/projects` (CARD-728). In Docker, project commands run inside the container, so the container needs that folder mounted from the host (like the wiki) and the toolchains a project build needs. CARD-730's git tools read `GITHUB_TOKEN`, so compose must pass it through.

## Goal
- `docker compose up -d` mounts `/data/projects` from `AUTOREIV_PROJECTS_HOST_PATH` (or the `autoreiv-projects` volume), and the serve sees `AUTOREIV_PROJECTS_DIR=/data/projects`.
- The operator can open the same host folder in VS Code while AutoReiv works on it; git inside the container does not refuse repos owned by the host user.
- The image has Python 3.12, git, Node.js 22 (npm, npx, corepack), uv/uvx, make, g++ and Godot 4 headless.
- `GITHUB_TOKEN` set on the host reaches the container for private GitHub clones and pushes.

## Change
- `Dockerfile` (runner stage):
  - apt adds `make` and `g++` (not full `build-essential`).
  - Node.js 22: `COPY --from=node:22-bookworm-slim` of `/usr/local/bin/node` and `/usr/local/lib/node_modules`, plus `npm`, `npx`, `corepack` symlinks (arch independent).
  - `COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /usr/local/bin/`.
  - `ARG INSTALL_GODOT=1`, `ARG GODOT_VERSION=4.7.2`, `ARG TARGETARCH`: downloads `Godot_v<ver>-stable_linux.{x86_64|arm64}.zip` from GitHub releases with Python (no curl/unzip in the image), installs `/usr/local/bin/godot`, runs `godot --headless --version` as a build check.
  - `mkdir /data/projects` (owned by `autoreiv`; `/data/wiki` still not created, ADR-0056).
  - `git config --global --add safe.directory '*'` for `autoreiv` (bind-mounted repos are owned by host uids). The CARD-722 `.git` copy and `safe.directory /app` are unchanged.
  - `templates/` is retired by CARD-729: the `COPY templates/` line and `'/templates/**'` in the `git sparse-checkout set` list are removed.
  - `ENV AUTOREIV_PROJECTS_DIR=/data/projects`.
- `docker-compose.yml`: env `AUTOREIV_PROJECTS_DIR=/data/projects`, `GITHUB_TOKEN=${GITHUB_TOKEN:-}`; volume `${AUTOREIV_PROJECTS_HOST_PATH:-autoreiv-projects}:/data/projects` with Windows/Linux examples; named volume `autoreiv-projects`.
- Docs: `docs/install-and-uninstall.md` (Docker), `deploy/README.md` (Docker), `.env.example`: projects mount, VS Code on the same folder, toolchains, Unity/Unreal not supported in the container, `GITHUB_TOKEN`.

## What dies
Nothing.

## Proof
- No UI, so no browser journey (`proof.journeys: []`).
- Guard test `tests/unit/deploy/test_card731_docker_projects_and_toolchain.py` (ADR-0067): compose mounts `/data/projects` from `AUTOREIV_PROJECTS_HOST_PATH`, sets `AUTOREIV_PROJECTS_DIR` and `GITHUB_TOKEN`; runner stage sets `AUTOREIV_PROJECTS_DIR`, creates `/data/projects` (and not `/data/wiki`), sets `safe.directory '*'`, copies node/npm/npx and uv, installs make/g++, and has `ARG INSTALL_GODOT=1`, `ARG GODOT_VERSION`, `TARGETARCH`, `/usr/local/bin/godot`; CARD-722 update machinery kept. 6 of 7 failed before the change.
- `tests/unit/deploy/test_deploy_suite.py::test_dockerfile_templates_and_layout` renamed `test_dockerfile_layout` and now asserts the image does not copy `templates/` (retired by CARD-729).
- Docker smoke: `docker build -t autoreiv-card731-test .` from a clean clone of the branch, toolchain versions inside the container, a run with a host projects bind mount and a wiki bind mount until `/api/health` is 200, `git init` in `/data/projects/demo` from inside the container.

## Plan and decisions
- Architecture was decided in ADR-0067 (`build` given). Engineering details recorded here:
  - Node from the official image by `COPY --from` rather than NodeSource apt: same binary on amd64 and arm64, no extra apt repo.
  - uv pinned to `0.13.1` (current release) for reproducible builds.
  - Godot `4.7.2` (current 4.x stable on github.com/godotengine/godot/releases). Downloaded with the image's Python so no `curl`/`unzip` lands in the image. `libfontconfig1` is installed with it (Godot printed `libfontconfig.so.1: cannot open shared object file` without it; `SystemFont` needs it). `INSTALL_GODOT=0` leaves both out.
  - `safe.directory '*'` instead of per-path entries: repos under `/data/projects` are created or cloned at runtime and may be owned by any host uid; the container runs one user, so the ownership check adds no protection there.
  - `make` + `g++` instead of `build-essential` to keep the image lean; `g++` pulls `gcc` and libc headers, enough for node-gyp and most pip sdists.

## Findings
- (fixed) Godot headless printed `libfontconfig.so.1: cannot open shared object file` on every start; `libfontconfig1` added with Godot.
- (open, for the lead) Plain `git init` in the container prints the "Using 'master' as the name for the initial branch" hint and makes `master`. CARD-728's `create_project` should pass `-b main` (or the image could set `init.defaultBranch main`); not changed here.
- (open, for the lead) Until CARD-729 lands, a container built from this branch has no `templates/sdlc-project`, so the old `create_project` template copy would fail inside Docker. Intended ordering per the lead: CARD-731 merges first, CARD-729 right after.
- Building from a git worktree fails the CARD-722 `COPY .git/` step's purpose (`.git` is a pointer file there), so the smoke image was built from a clean `git clone` of the branch under `scratch/card731/build`. Real installs are normal clones.

## Results
| Check | Result | Notes |
|---|---|---|
| Guard test before change | FAIL (expected) | 6 failed, 1 passed (CARD-722 machinery check) |
| Guard test after change | PASS | 7 passed; `tests/unit/deploy` 39 passed, 4 skipped |
| `docker build -t autoreiv-card731-test .` (aarch64) | PASS | Godot build check printed `4.7.2.stable.official.ed1daf0bf` |
| Toolchain in container | PASS | node v22.23.3, npm 10.9.9, npx 10.9.9, corepack 0.36.0, uv 0.13.1, Python 3.12.15, git 2.47.3, GNU Make 4.4.1, g++ 14.2.0, godot 4.7.2.stable.official.ed1daf0bf (no fontconfig error) |
| Image env and folders | PASS | `safe.directory` = `/app`, `*`; `/data/projects` owned by `autoreiv`; `AUTOREIV_PROJECTS_DIR=/data/projects`; no `/data/wiki` dir baked in; `/app` = README.md, platform, pyproject.toml, src; sparse list without templates |
| Run with host projects + wiki bind mounts on :8791 | PASS | `GET /api/health` -> 200 (`version 1.4.1`); Docker health `healthy` after 35 s |
| `git init -b main` + commit in `/data/projects/demo` | PASS | `## main`, commit created; host folder shows `demo` owned by uid 1000 |
| Repo owned by another uid (root) | PASS | `git status` works as `autoreiv`; control with `HOME=/tmp` (no safe.directory) fails `detected dubious ownership` |
| Image size | 964 MB | was 405 MB (`autoreiv-autoreiv:latest`, current qa image); Node, g++ and Godot are most of the growth |
| `preflight.py --fast --base qa` | GREEN | ruff PASS, eslint SKIP, pytest guard PASS (305), changed tests PASS (13), mapped SKIP, vitest PASS (1139) |
| Cleanup | PASS | smoke container removed, `docker rmi autoreiv-card731-test` (and its two superseded untagged builds), scratch folder removed; existing containers untouched |

## Release note
Docker: the projects folder is mounted at `/data/projects` (`AUTOREIV_PROJECTS_HOST_PATH`), `GITHUB_TOKEN` is passed through, and the image ships Node.js 22, npm, uv, make, g++ and Godot headless for project work.
