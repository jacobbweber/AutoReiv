---
name: release
description: Release qa into main when Jacob says 'release': run preflight --release, bump version across all 6 canonical files, merge qa -> main (--no-ff), tag vX.Y.Z, push qa/main/tag, prune stale local and remote branches, and rebuild/restart serve.
---
# Release (`qa` -> `main`)

Run ONLY when Jacob says `release` (or explicitly asks to merge `qa` into `main` and cut a release) in the current session.

## 1. Release Gate (`preflight --release`)
Run the full release preflight suite from `qa`:
```bash
export PATH="/home/spark/autoreiv/.venv/bin:/home/spark/.openclaw/tools/node-v24.21.0/bin:$PATH"
.venv/bin/python .agents/skills/preflight/scripts/preflight.py --release
```
Stop and report if any stage is RED.

## 2. Version Bump on `qa`
Determine the next version `X.Y.Z` (default: increment patch `X.Y.(Z+1)` from `pyproject.toml` unless Jacob names a minor/major bump). Update all 6 canonical version locations on `qa`:
1. `pyproject.toml`: `version = "X.Y.Z"`
2. `package.json`: `"version": "X.Y.Z"`
3. `uv.lock`: `version = "X.Y.Z"` under `[[package]] name = "autoreiv"`
4. `src/application/system/update_git_ops.py`: fallback `return "X.Y.Z"` in `_read_local_version`
5. `CHANGELOG.md`: add `## [X.Y.Z] - YYYY-MM-DD` with a 1-sentence summary immediately below `## [Unreleased]`
6. `steering/roadmap.md`: append `- [x] **X.Y.Z released YYYY-MM-DD** (tag \`vX.Y.Z\`): <summary>.` under `## Shipped`

Commit on `qa`:
```bash
git add pyproject.toml package.json uv.lock src/application/system/update_git_ops.py CHANGELOG.md steering/roadmap.md
git commit -m "chore(release): bump version to X.Y.Z"
```

## 3. Merge `qa` into `main` & Tag
```bash
git switch main
git pull --ff-only origin main
git merge --no-ff qa -m "merge: qa into main (release vX.Y.Z)"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin qa main vX.Y.Z
git switch qa
```

## 4. Clean Up Stale Branches & Worktrees
Prune worktrees, remote tracking refs, merged local branches (keeping `main` and `qa`), and merged remote `feat/*` / `fix/*` branches:
```bash
git worktree prune
git fetch --prune origin
git branch --merged qa | grep -vE '^\*|^\s*(main|qa)$' | xargs -r git branch -d
for rbranch in $(git branch -r --merged origin/qa | grep -E 'origin/(feat|fix|chore|docs)/' | sed 's| *origin/||'); do
  git push origin --delete "$rbranch"
done
```

## 5. Rebuild & Verify Live Server
Rebuild and restart the live service so `/api/health` and `/api/system/update-status` report `vX.Y.Z`:
- Linux/Docker (Spark): `docker compose up -d --build && curl -s http://127.0.0.1:8000/api/health`
- Windows (Jarvis): `pwsh -NoProfile -File scripts\restart_serve.ps1 -HostAddr 0.0.0.0 -Port 8000`

## 6. Report
Report to Jacob:
- Released version and tag (`vX.Y.Z`)
- `preflight --release` result table
- Commit hashes on `qa` and `main`
- Branches/worktrees cleaned up
- Live health status on `:8000`
