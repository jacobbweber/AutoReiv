---
trigger: always_on
description: The only Done checklist. A machine loop can check every line.
---
# Definition of done

## In Review needs all of
- [ ] Card front matter has `status`, `priority`, `milestone`, `proof.journeys`, `proof.checks`, `log`.
- [ ] Card body has Problem (or Intent), Cause (bugs), Change, What dies, Findings, Release note.
- [ ] Each changed behaviour has a test that failed before the change.
- [ ] Everything under "What dies" is deleted; the Scavenger `rg` finds no orphans.
- [ ] `preflight.py --fast` is GREEN (known failures only as KNOWN or XFAIL with a card id). No full suite; that is the release gate (qa -> main).
- [ ] Every journey in `proof.journeys` passes on desktop and phone. Known bugs show XFAIL with a card id.
- [ ] Results table and 2-3 screenshot paths are in the card.
- [ ] An ADR with a guard test exists if the change adds a decision that constrains code.
- [ ] `git status` shows nothing untracked outside `scratch/`.

## Done needs
- [ ] Jacob said `merge to qa` for this card.
- [ ] Skill `merge-to-qa` finished: merged `--no-ff`, CHANGELOG line added, pushed, branch deleted.
