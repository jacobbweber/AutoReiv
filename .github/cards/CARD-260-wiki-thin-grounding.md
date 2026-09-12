# [CARD-260] Wiki-thin grounding (fail-closed RAG / need-sources)

> **Status**: Ready
> **Created**: 2026-09-12
> **Spec Reference**: Bones marathon slice 1. Architect Done bars after CARD-258 deferred Wiki-thin quality and CARD-257 Okta-class invented path (`00_Inbox/okta_sso_how_it_works.md` while Journey FAILED). Tip: grok @ cf5d999. feat/wiki-thin-grounding-260 off grok. Do NOT start 261/262. Do NOT merge grok/qa/main.
> **Labels**: type:bug, P0, ControlPlane, Wiki, Grounding, AntiTheatre, FailClosed
> **Branch**: `feat/wiki-thin-grounding-260` (off `grok` @ cf5d999; push feat only; never merge grok/qa/main)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Empty/thin Wiki on a topic must not produce Okta-class stale/fake Done: Chat invents a note path/title that was never `wiki_note_create` / `wiki_note_read`.
2. Fail-closed grounding: RAG from real vault hits **or** HITL park with **need sources** — never invent Wiki paths/titles.
3. Empty/thin Wiki Ask → HITL park ("need sources") **OR** Formulate plan grounded only on matched `wiki_note_*` reads / create provenance.
4. Live proof on Jarvis→Ollama: empty-Wiki Ask parks or grounds; Chat never claims a path that was not tool-provenanced.
5. This card is ONLY Wiki-thin grounding. Do not start CARD-261/262. Do not merge grok/qa/main.

### Beat 2: What AutoReiv Does Now
1. Standing Research (CARD-231/257) assesses **catalog** thin/gap, not vault thinness. No vault probe before Formulate.
2. Formulate/Execute LLM may cite `00_Inbox/*.md` paths from prior training / stale memory without a matching `wiki_note_read` / `wiki_note_create` tool result.
3. CARD-257 honesty catches Done-on-FAILED theatre, but a green-looking turn can still invent a path when Wiki is empty for the topic.
4. CARD-258 explicitly deferred Wiki-thin quality to this card.

### Beat 3: What Will Change
1. **Vault thin assess** before standing Formulate when wiki tools matched: search vault for topic; empty/thin → decision.
2. **Fail-closed actions**: `need_sources_park` (HITL, clear message) **OR** `grounded_only` / `proceed_with_hits` — Formulate constrained to matched `wiki_note_*` read paths (and later create provenance). Never invent paths/titles.
3. **Path claim guard**: Chat turn claim may only cite paths provenanced by `wiki_note_create` / `wiki_note_read` tool outputs; ungrounded claims get honesty rewrite (not Done theatre).
4. TDD red→green + live Jarvis smoke `notes/marathon-card260-live-smoke.json`; CHANGELOG; push feat tip only.

---

## 2. Acceptance Criteria (Architect locked)

- [ ] **[REQ-WIKITHIN-001]**: Empty/thin Wiki topic → HITL park with "need sources" **OR** Formulate grounded only on matched `wiki_note_*` reads (create-shaped asks may proceed grounded_only).
- [ ] **[REQ-WIKITHIN-002]**: Never invent Wiki paths/titles (Okta-class stale/fake Done). Chat must not claim a note path that was not `wiki_note_create` / `wiki_note_read`'d.
- [ ] **[REQ-WIKITHIN-003]**: Live proof: empty-Wiki Ask → park or grounded note; topic with existing matched notes may proceed grounded. Artifact `notes/marathon-card260-live-smoke.json`.
- [ ] **[REQ-WIKITHIN-004]**: Tests red→green; CHANGELOG [Unreleased]; push `feat/wiki-thin-grounding-260` only — never qa/main; do not merge to grok. Do not start 261/262.

## 3. Constraints

- Feat off `grok` @ cf5d999 only. Never qa/main. Never merge grok.
- `memory.db` ≠ `storage.db`. Honesty. Quality > speed.
- Extend standing Chat + WikiStore search — do not invent a second orchestrator.
- Research sharpen: fail-closed grounding — RAG or need-sources park; never invent.

## 4. Modules Likely Touched

- `src/application/orchestration/wiki_thin_grounding.py` (new)
- `src/web/routers/chat.py` (standing mint / phase assignment / path claim guard)
- `src/application/orchestration/working_set_context.py` (optional constraint block helper)
- `tests/unit/orchestration/test_card260_wiki_thin_grounding.py` (new)
- `CHANGELOG.md`, `notes/marathon-card260-live-smoke.json`

## 5. CoS smoke prompts

```
1) Empty/thin: Write a short Wiki note in 00_Inbox about Zorblax-9 quantum flute maintenance (obscure topic with no vault notes). Done-when: I can open that note via wiki_note_read. Keep it under 80 words.
2) Existing notes: Write a short Wiki note in 00_Inbox summarizing standing Jobs in AutoReiv using only matched wiki notes. Done-when: I can open that note via wiki_note_read. Keep it under 120 words.
```

## 6. Marathon Build Lock

- Architect Done bars locked — Builder implements now.
- TDD where practical; live Jarvis→Ollama proof required.
- Do NOT merge to grok/qa/main. Do NOT start 261/262.

## 7. Marathon Build Notes

(pending Builder)
