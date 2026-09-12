# [CARD-241] Education Wiki tools allowlist - no bare wiki_overview

> **Status**: Done (merged grok @ 19f6e6b)
> **Created**: 2026-09-11
> **Spec Reference**: Architect Done bar - Priming/Dual Coding only call catalog-matched wiki_note_*; unregistered fail soft / skip
> **Labels**: type:bug, P1, Education, Wiki, AntiTheatre
> **Branch**: `feat/education-wiki-overview-241` (off `grok` @ ed41e03)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Education Priming Ask should land a Wiki schema note in Inbox and hit `success_rule`.
2. Live job_f82aacf3399c: Execute FAILED because `wiki_overview` returned ERR (0ms). Chat UI may show Complete but Journey shows ERR.
3. Priming / Dual Coding must only call catalog-matched `wiki_note_*` (search/read/list/create[/append]) - never bare `wiki_overview`.
4. One unregistered / out-of-subset tool call must fail soft / skip - not kill Execute mid-flight.

### Beat 2: What AutoReiv Does Now
1. Education skill seeds already list `wiki_note_*`, but the agent pack still grants `wiki_overview`, Wiki SKILL.md still recommends it, and job-bound turns expose the full agent tool list.
2. Standing Jobs lock matched capability IDs; ToolPolicyGate BLOCKs tools outside the matched subset (fail closed) with ~0ms ERR.
3. Model calls `wiki_overview` (listed but not Education-matched) -> BLOCK -> Journey ERR -> Execute dies before Inbox note / `success_rule`.
4. Skill-only matched IDs (`skill.education-priming`) were treated as bare tool names, which can empty/poison the capability tool subset.

### Beat 3: What Will Change
1. Education Priming / Dual Coding skills (+ Ask shaping) explicitly allowlist catalog-matched `wiki_note_*` and forbid `wiki_overview` / `wiki_graph`.
2. Wiki runbook stops pushing `wiki_overview` as the default topology call; prefer `wiki_note_list` / `wiki_note_search`.
3. Kernel / ToolPolicyGate: unregistered or out-of-matched-subset calls fail soft / skip (guidance to use `wiki_note_*`) so Execute can still create the note; explicit block_tools / allowlist / dangerous stay hard BLOCK.
4. Matched capability tool subset ignores `skill.*` / `agent.*` / `pack.*` / `routine.*` IDs; Education skill matches expand to the `wiki_note_*` allowlist (never `wiki_overview`). Job-bound active tools prefer that subset.

---

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-EDU-WIKI-001]**: Priming / Dual Coding skill seeds and Education Ask shaping only call catalog-matched `wiki_note_search` / `wiki_note_read` / `wiki_note_list` / `wiki_note_create` (optional `wiki_note_append`). No bare `wiki_overview`.
- [x] **[REQ-EDU-WIKI-002]**: Unregistered or out-of-matched-subset tool calls fail soft / skip (do not abort Execute). Explicit policy blocks remain fail-closed.
- [x] **[REQ-EDU-WIKI-003]**: Proof: Priming Ask lands a note in Wiki `00_Inbox/` and hits `success_rule` without Execute dying mid-flight on `wiki_overview` ERR (0ms). Feat off `grok` only; do not merge until asked.

## 3. Constraints

- Feat off `grok` only. Never qa/main. Do not merge to grok unless asked.
- Prefer skills only call matched `wiki_note_*`; unregistered fail soft.
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first (pytest and/or skill seed tests).

## 4. Hypothesis (verify in TDD)

`wiki_overview` is registered in WikiTools / pack grants (not a total ghost) but is outside Education matched `wiki_note_*` subset. Model still sees/calls it -> ToolPolicyGate BLOCK @ 0ms -> Execute fails. Fix = skills/prompts allowlist + soft-skip unknown/out-of-subset + Education matched expansion to `wiki_note_*` only.

## 5. Proof

- Pytest: education seeds never mention `wiki_overview`; unknown/out-of-subset fail-soft does not abort; Priming path can still create note.
- Operator: Education -> Priming Ask -> Inbox note + Journey without `wiki_overview` ERR kill.

