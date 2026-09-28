---
name: merge-to-qa
description: The batched merge after Jacob says "merge to qa". Use only then.
---
# Merge to qa

Only for the cards Jacob named in `merge to qa`. Never reset `qa`. Stop and report on any unexpected state.

1. `git status` is clean. `git switch qa`. `git log -1` is the tip you expect.
2. For each branch, in the order Jacob gave (or oldest first):
   1. On the branch: set each card `status: Done`, add `completed: YYYY-MM-DD`, commit `docs(card-N): Done`.
   2. `git switch qa && git merge --no-ff feat/card-N-slug -m "merge: CARD-N <title>"`.
   3. Resolve conflicts by keeping both sides. Branches never edit CHANGELOG or roadmap, so conflicts should be rare.
   4. Add each card's Release note line to `CHANGELOG.md` under `## [Unreleased]` (Added / Changed / Fixed), then `git commit --amend --no-edit` on the merge commit. Skip if the line is already there.
   5. Fast tier against the old remote tip: `preflight.py --fast --base origin/qa` (`--base qa` sees no changes once merged).
3. Roadmap is milestones only: if these cards finish a milestone, tick it in `steering/roadmap.md` (commit `docs(roadmap): M<N> done`). Never add per-card lines.
4. No full suite here. The full suite is the release tier, run only before merging qa into main (skill `preflight`).
5. `git push origin qa` once. Report the range (`<old>..<new>`).
6. `git branch -d <branch>` for each merged branch (`-d`, never `-D`). `git worktree list` shows only the checkout.
7. Restart serve: `pwsh -NoProfile -File scripts\restart_serve.ps1 -HostAddr 0.0.0.0 -Port 8000`.
8. Health: `Invoke-WebRequest http://127.0.0.1:8000/api/health` and `http://192.168.1.99:8000/api/health` both return 200.
9. Delete your own files in `scratch/`, except files an open card still needs (name that card in the report). `git status` clean.
10. Report: merge hashes, push range, fast-tier table, health, branches deleted.

Commit messages: `type(scope): summary [CARD-N]`, where type is one of feat, fix, refactor, test, docs, chore.
