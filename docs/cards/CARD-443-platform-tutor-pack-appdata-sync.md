---
id: CARD-443
title: "Promote Platform Tutor Packs into AppData Local Without Manual Copy"
status: Ready
created: 2026-09-23
adr: none
labels:
  - type:architecture
  - area:tutor
  - area:packs
  - P1
parent: CARD-436
related:
  - CARD-435
---

# [CARD-443] Promote Platform Tutor Packs into AppData Local Without Manual Copy

> **Status**: Ready
> **Created**: 2026-09-23
> **Observed during**: CARD-436 live-test on `feat/card-436-inventory-tutor-learning-os-rails`
> **ADR Reference**: none (add one only if pack promotion becomes a lasting deployment contract)
> **Labels**: `type:architecture`, `area:tutor`, `area:packs`, `P1`
> **Parent**: [CARD-436](./CARD-436-inventory-tutor-learning-os-rails.md)
> **Wave**: [CARD-435](./CARD-435-education-tutor-first-direction.md)  ->  CARD-436 follow-up

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine the promotion trigger, user-modified policy, or proof path - **still no product code** |
| **`build`** | Implement platform-pack promotion/sync and its tests; do not manually copy the live pack as the implementation |
| **`merge to qa`** | After implementation proof shows a clean Tutor promotion and an explicit user-modified failure mode |

Do not write product code until Jacob says **build** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on** | [CARD-436](./CARD-436-inventory-tutor-learning-os-rails.md) for the Tutor Learning OS skill ids and platform-pack source |
| **Related** | [CARD-435](./CARD-435-education-tutor-first-direction.md) for the Tutor-first wave and promotion boundary |
| **Blocked by** | Nothing; this card is a docs-only Ready follow-up and may be implemented independently on `qa` after the feat branch lands |
| **Unlocks** | Reliable live Tutor skill visibility after platform-pack changes; the same promotion contract for other `platform-packs/<pack>/` directories |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. A change committed under `D:\Projects\Active\AutoReiv\platform-packs\` must reach the pack directory used by the running AutoReiv application without a manual copy or merge.
2. Tutor is the concrete failure found during the CARD-436 live-test: the platform branch contained new Learning OS skills, while the live pack at `C:\Users\jacob\AppData\Local\AutoReiv\packs\tutor\` still contained only `socratic-tutoring` until it was manually merged.
3. The live pack reported `user_modified: None`, so this was a missing platform-to-AppData promotion/sync path, not an operator lock. The implementation must still define the locked/user-modified failure mode instead of overwriting operator content.

### Beat 2: What AutoReiv does now

1. Platform pack source is `D:\Projects\Active\AutoReiv\platform-packs\tutor\`, including `pack.json` and `skills\<skill-id>\SKILL.md`.
2. The live local pack is `C:\Users\jacob\AppData\Local\AutoReiv\packs\tutor\`, which is the directory the running application reads for Tutor skills.
3. CARD-436 platform-branch updates were not visible after the application restart/reload because the AppData copy was stale. The new skills appeared only after a manual merge into the AppData pack.
4. The observed clean state was `user_modified: None`; no operator-owned local edit prevented promotion.

### Beat 3: What will change

1. Add one explicit promotion/sync path for `platform-packs\<pack>\` to `C:\Users\jacob\AppData\Local\AutoReiv\packs\<pack>\` at the application lifecycle point that owns pack discovery, installation, restart, or reload. The chosen trigger and source-of-truth rule must be documented in the implementation.
2. When the destination pack is not user-modified (`user_modified` is `None`), promote the platform manifest and skills so a restart/reload exposes the platform Tutor skill ids without manual file copying.
3. When the destination pack is user-modified, do not overwrite it. Surface a deterministic skip/failure reason and an operator-visible resolution path; preserve the local pack and prove that the platform update remains unapplied until the operator resolves the conflict.
4. Apply the same contract to platform packs generally, while using Tutor as the required acceptance fixture. Do not special-case only `socratic-tutoring` or only the CARD-436 skill names.
5. Add an automated contract test or equivalent deterministic check for clean promotion, stale-destination repair, and the user-modified refusal path. The proof must identify both the platform source and AppData destination paths.

**Out of scope:** creating or renaming the CARD-436 Tutor skills; changing Tutor pedagogy; silently overwriting user-modified packs; a manual one-time merge; unrelated pack content authoring; merging to `main`; and version bump work.

### Beat 4: What dies today

1. The running app silently using a stale AppData Tutor pack after a platform-pack update.
2. The requirement that an operator manually merge `platform-packs\tutor\` into the AppData pack before new skill ids can appear.
3. Ambiguity about whether a missing skill is caused by a stale promotion or by an intentional user-modified lock.

---

## 2. Acceptance criteria

- **[REQ-443-001]** WHEN a checked-in `platform-packs\<pack>\` manifest or skill changes, THE SYSTEM SHALL have an explicit platform-to-AppData promotion/sync path that updates `C:\Users\jacob\AppData\Local\AutoReiv\packs\<pack>\` without a manual copy or merge.
- **[REQ-443-002]** WHEN the Tutor AppData pack has `user_modified: None`, a restart or reload SHALL make every Tutor skill id declared by `D:\Projects\Active\AutoReiv\platform-packs\tutor\pack.json` and its `skills\` directories visible to the running app, including the CARD-436 ids `start-resume-topic`, `quiz-turn`, `flashcard-turn`, `due-review`, `education-wiki-curation`, and `progress-summary` alongside `socratic-tutoring`.
- **[REQ-443-003]** WHEN the AppData destination pack is user-modified, THE SYSTEM SHALL NOT overwrite operator content. It SHALL expose a deterministic skipped/blocked promotion result that names the user-modified condition and gives the operator a resolution path.
- **[REQ-443-004]** THE SYSTEM SHALL use the same promotion rule for platform packs generally, not a Tutor-only or skill-name-only workaround.
- **[REQ-443-005]** THE PROOF SHALL record the exact source paths under `D:\Projects\Active\AutoReiv\platform-packs\`, the exact destination paths under `C:\Users\jacob\AppData\Local\AutoReiv\packs\`, the pre-promotion stale state, the restart/reload action, and the post-promotion visible skill ids.
- **[REQ-443-006]** Automated coverage or a deterministic operator check SHALL cover clean promotion, stale destination repair, and refusal to overwrite a user-modified destination. A manual merge SHALL not count as proof of promotion.

---

## 3. Proof / live-test notes

1. Capture the source inventory from `D:\Projects\Active\AutoReiv\platform-packs\tutor\pack.json` and `D:\Projects\Active\AutoReiv\platform-packs\tutor\skills\`; capture the stale destination inventory from `C:\Users\jacob\AppData\Local\AutoReiv\packs\tutor\` before promotion.
2. With the destination reporting `user_modified: None`, trigger the implemented restart/reload or promotion lifecycle. Confirm that the destination contains the platform manifest and skill files, then confirm in the running app's Tutor skill list that all CARD-436 ids appear without manual copying.
3. Exercise a user-modified fixture or controlled destination. Confirm that local content remains unchanged, the promotion result names the user-modified condition, and the operator receives the documented resolution path.
4. Repeat the check for one non-Tutor platform pack or a generalized contract fixture to prove this is platform-pack promotion rather than a Tutor-only patch.
5. A missing skill after clean promotion is a failure of this card. A missing skill with a user-modified destination is expected only when the blocked result and resolution path are visible and proven.

---

## 4. Constraints

- This card is docs-only scaffolding until Jacob says **build**.
- The follow-up is intentionally on the current `feat/card-436-inventory-tutor-learning-os-rails` branch so it can merge with CARD-436; implementation may land on `qa` independently after that merge.
- Do not manually merge the live Tutor pack as a substitute for implementation or proof.
- Do not overwrite a user-modified AppData pack.
- Do not merge to `qa` until the exact live-test proof is complete, and do not merge to `main`.
- Do not create a GitHub PR or bump the version for this docs-only scaffold.
- Use plain full sentences, exact paths, and the gate phrases **continue**, **build**, and **merge to qa**.

---

## 5. Reply phrases

- Refine the promotion contract: say **continue**.
- Start implementation: say **build**.
- After clean and user-modified live proof: say **merge to qa**.

## 6. Finding from CARD-444 live test

During the CARD-444 sync, AppData `pack.json` and `SKILL.md` were updated and serve was restarted, but Tutor's SQLite-backed agent profile `system_prompt` stayed on the old prompt: `GET /api/agents/tutor` lacks the CARD-444 clause. CARD-443 must also resync the pack `system_prompt` into the stored agent profile without clobbering user edits such as `max_turns=100`.
