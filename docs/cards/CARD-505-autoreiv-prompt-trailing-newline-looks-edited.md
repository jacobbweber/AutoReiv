---
id: CARD-505
title: "AutoReiv's system prompt looks operator-edited on every restart (trailing newline), so platform prompt updates never land"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-443
  - CARD-449
  - CARD-450
  - CARD-502
labels:
  - type:bug
  - area:agents
  - P2
---

# [CARD-505] AutoReiv's system prompt looks operator-edited on every restart (trailing newline), so platform prompt updates never land

> **Status**: Ready
> **Created**: 2026-09-25 (found in the CARD-502 scratch repro)
> **Related**: CARD-443 (platform promotion), CARD-449 (content lock), CARD-450 (Platform defaults badge), CARD-502
> **Labels**: `type:bug`, `area:agents`, `P2`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Four Beats

**Beat 1: What Jacob means.** If I never edited AutoReiv's system prompt, a platform update to that prompt reaches my AutoReiv, and saving an unrelated setting in Agent Studio does not freeze it.

**Beat 2: What AutoReiv does now.** Seen on a freshly wiped scratch data folder (`scratch/c500_data`, 2026-09-25, `scratch/c502_prompt.py` / `c502_prompt2.py`): `platform-packs/autoreiv/pack.json` `system_prompt` ends with a newline (3,161 characters); the stored copy in SQLite `custom_agents` has 3,160 (the guardrail strips it, `src/domain/agents/guardrails.py` L58). The shipped baseline hash in setting `platform_shipped_prompt_hashes` is taken from the seed text with the newline. So on the first restart the sync report says autoreiv `promoted_partial`, "skipped fields: system_prompt" (`platform_pack_promotion.py` L672-690), and every later platform prompt change is skipped. `should_set_content_lock` (L164-169) compares the stripped Agent Studio prompt to the same baseline, so by that code path any Agent Studio Save on AutoReiv (even Max Turns only) sets `user_modified` (read from the code, not yet run; the first failing test will confirm it). Direct, Developer and Tutor seeds have no trailing newline and are not affected.

**Beat 3: What will change.** Prompt comparisons (baseline hash, divergence check, content lock) use the same normalized text (line endings unified, outer whitespace stripped), and a one-time startup fix clears a false "prompt skipped" state for packs whose stored prompt equals the seed after normalizing. Optionally strip the trailing newline from the AutoReiv seed too.

**Beat 4: What dies.** The false "skipped fields: system_prompt" for AutoReiv and false content locks caused by whitespace.

## 2. Acceptance criteria (EARS)

- **[REQ-505-001]** THE prompt baseline hash, `pack_content_diverged_from_seed` and `should_set_content_lock` SHALL compare normalized prompt text (CRLF to LF, outer whitespace stripped).
- **[REQ-505-002]** WHEN a platform pack's stored prompt equals its seed after normalizing, THE startup sync SHALL NOT report `system_prompt` as skipped.
- **[REQ-505-003]** WHEN Jacob saves only scalar fields (Max Turns, model) for AutoReiv in Agent Studio, THE SYSTEM SHALL NOT set `user_modified`.
- **[REQ-505-004]** A real operator prompt edit SHALL still lock and be preserved (existing CARD-449 behavior).

## 3. Decisions (recommendations)

| # | Question | Recommendation |
|---|----------|----------------|
| D1 | Fix in code, seed, or both | **Both:** normalize in code (protects every pack) and drop the trailing newline in the AutoReiv seed |
| D2 | Existing installs already falsely locked by a scalar save | **Reuse `migrate_false_content_locks`** (L276-340) with normalized comparison; it already writes a report |

## 4. Failing-tests-first plan

- pytest: seed prompt with trailing newline plus stored stripped copy: promotion reports `promoted`, not `promoted_partial` (red today); scalar-only `PUT /api/agents/autoreiv` leaves `user_modified` false (red today); a real prompt edit still locks (control).
- pytest integration: fresh data folder, two app starts: second sync report has no skipped `system_prompt` for autoreiv (red today).

## 5. Runbook

1. Settings > Platform packs sync report (or Agent Studio > AutoReiv > Platform defaults): after a restart, AutoReiv shows no "partly applied / system prompt kept" note when you never edited it.
2. Agent Studio > AutoReiv: change Max Turns only, Save, restart serve: the Platform defaults section still says up to date (no customized badge).
