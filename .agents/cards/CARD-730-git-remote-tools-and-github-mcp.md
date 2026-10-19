---
id: CARD-730
title: "AutoReiv clones, pulls and pushes git repos and can use GitHub's MCP server"
type: feature
status: Done
completed: 2026-10-19
priority: P1
milestone: M32
needs_decision: none
proof:
  journeys: [card-730-git-remote-tools]
  checks: [tests/unit/skills/test_card730_git_remote_tools.py, tests/unit/mcp/test_remote_sse_adapter.py]
branch: feat/card-730-git-remote-tools-and-github-mcp
log: {minutes: 75, qa_runs: 1, findings: 2}
created: 2026-10-19
---

# CARD-730 AutoReiv clones, pulls and pushes git repos and can use GitHub's MCP server

## Intent
Jacob wants AutoReiv to establish a project from GitHub (or any git host), keep it in sync and share work, and to use
GitHub's MCP server for issues and pull requests, configured by him as a user (ADR-0067, approved with `build`
2026-10-18). Until now AutoReiv could only create an empty repo and commit locally.

## Goal
- In Chat, "clone https://github.com/owner/repo" puts the repo in the projects folder and makes it the active project.
- AutoReiv can pull (fast-forward only) and push a work branch; it never force-pushes and never pushes main, master
  or qa. Each call asks for approval.
- Private GitHub repos work when the serve has `GITHUB_TOKEN`; the token is never written into the repo or shown.
- Jacob can add `https://api.githubcopilot.com/mcp/` in Capabilities with a Vault token and AutoReiv can talk to it.

## Change
- New `src/application/sdlc/git_remote.py`: `remote_env(url)` (no prompts, `GIT_ALLOW_PROTOCOL=https:ssh:file`, the
  GitHub token as a `GIT_CONFIG_*` extra header for github.com only), `scrub()` for output, `check_remote_url()`
  (https, ssh, git@host:path; local repos only inside the projects folder; refuses credentials in the URL, option
  injection, `ext::`, the running checkout).
- `src/application/sdlc/projects_service.py`: `git_clone(url, slug, select)` tool (jail, timeout, cleanup on failure,
  `ensure_commit_identity`, selects the project). `_touches_running_checkout` becomes public `touches_running_checkout`.
- `src/application/skills/git_tools.py`: `git_pull` (`pull --ff-only origin <branch>`) and `git_push`
  (`push --set-upstream origin <branch>:<branch>`, refuses protected branches); `_run(remote=url)` adds the env and a
  timeout and scrubs output.
- `hitl_engine.py`, `tool_policy_gate.py`, `tool_access.py`: the three tools ask for approval and are WRITE tools.
- Skills: `git_clone` in `repo-onboarding`; `git_pull`, `git_push` in `software-development` (14 tools) with a new
  step 7 and `references/github.md` (token and GitHub MCP setup).
- `src/infrastructure/mcp/client_adapter.py`: the remote transport speaks Streamable HTTP: `Accept: application/json,
  text/event-stream`, SSE-framed replies, and the `Mcp-Session-Id` the server hands out (GitHub's server needs these).
- `docs/user-guide.md`: "GitHub repos" section.

## What dies
- Nothing (the private name `_touches_running_checkout` is renamed, not duplicated).

## Proof
- Journey `card-730-git-remote-tools` (desktop and phone), with a bare origin repo inside the projects folder:
  1. Chat asks AutoReiv to `git_clone` it; the approval card is approved; the project is on disk and active, and
     Projects Studio shows it.
  2. A new commit lands in origin; Chat asks for `git_pull`; after approval the local HEAD equals origin.
  3. A work branch with a commit exists; Chat asks for `git_push`; after approval origin has the branch.
  4. On `main`, `git_push` is refused and origin `main` is unchanged.
- Checks: `tests/unit/skills/test_card730_git_remote_tools.py` (real git: clone, refusals, pull ff-only and no merge
  commit, push branch and refuse main, token never in config or output, approval and skill binding),
  `tests/unit/mcp/test_remote_sse_adapter.py::test_remote_adapter_speaks_streamable_http_like_the_github_mcp_server`.

## Plan and decisions
- Product and architecture: approved in ADR-0067 (`build`, 2026-10-18).
- Technical:
  - The token rides in `GIT_CONFIG_COUNT/KEY/VALUE` env, not `-c` on the command line (visible in `ps`) and not a
    credential helper (would persist).
  - Pull is fast-forward only; diverged branches are the operator's call. Push mirrors `git_commit`'s protected list.
  - Local clone sources are limited to the projects folder so `git_clone` cannot copy arbitrary host folders.
  - Streamable HTTP support was needed for the GitHub MCP docs to be true; it is a protocol fix inside the existing
    remote transport (no new transport option in the UI).

## Findings
- (fixed) The remote MCP transport only sent `Content-Type: application/json` and read a plain JSON body, so Streamable
  HTTP servers (GitHub's) would answer 406 or an SSE frame it could not read. Now Accept, SSE replies and session id.
- (fixed) `askAndApprove` had three copies; the card-697 version moved to `tests/e2e/journeys/lib/app.mjs` and is used
  by card-697 and card-730.
- (logged) card-562 and card-563 still keep their own `askAndApprove` with a different signature.
- (logged) The GitHub MCP server was not exercised live: this host has no GitHub token. The protocol is covered by a
  unit test that mimics GitHub's replies; the first real run is when Jacob adds the server with his token.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-730-git-remote-tools | desktop | PASS | 5/5 steps; one approval each for clone, pull, push; push on main refused, origin main unchanged |
| card-730-git-remote-tools | phone | PASS | 5/5 steps |
| preflight --fast --base qa | - | GREEN | guard 314, changed 23, mapped 386, vitest 1139 |
| pytest tests/unit + tests/integration | - | PASS | 3076 passed after the tool-count update |

Screenshots:
- /tmp/autoreiv-qa/card-730/card-730-git-remote-tools-desktop-02-git-clone-after-approval-lands-in-the-projects-f.png
- /tmp/autoreiv-qa/card-730/card-730-git-remote-tools-desktop-05-git-push-on-main-is-refused-and-origin-main-is-u.png
- /tmp/autoreiv-qa/card-730/card-730-git-remote-tools-phone-04-git-push-after-approval-sends-the-work-branch-to.png

## Release note
Added: AutoReiv can clone repos into the projects folder and pull and push work branches (approval per call; private
GitHub repos via `GITHUB_TOKEN`), and remote MCP servers that speak Streamable HTTP, such as GitHub's
`https://api.githubcopilot.com/mcp/`, now work in Capabilities (CARD-730).
