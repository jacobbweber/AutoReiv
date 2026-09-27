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
   4. Add each card's Release note line to `CHANGELOG.md` under `## [Unreleased]` (Added / Changed / Fixed), then `git commit --amend --no-edit` on the merge commit.
   5. Fast tier (skill `preflight`).
3. After the last merge: full tier once (skill `preflight`). Skip it if `qa` did not move since the branch's own full run (`git rev-parse qa^1` equals the base the branch was tested on).
4. `git push origin qa` once. Report the range (`<old>..<new>`).
5. `git branch -d <branch>` for each merged branch (`-d`, never `-D`). `git worktree list` shows only the checkout.
6. Restart serve: `pwsh -NoProfile -File scripts\restart_serve.ps1 -HostAddr 0.0.0.0 -Port 8000`.
7. Health: `Invoke-WebRequest http://127.0.0.1:8000/api/health` and `http://192.168.1.99:8000/api/health` both return 200.
8. Delete your own files in `scratch/`. `git status` clean.
9. Report: merge hashes, push range, suite table, health, branches deleted.

Commit messages: `type(scope): summary [CARD-N]`, where type is one of feat, fix, refactor, test, docs, chore.
