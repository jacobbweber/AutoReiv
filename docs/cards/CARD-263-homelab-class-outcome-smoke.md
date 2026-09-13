# [CARD-263] Homelab-class outcome smoke (Wiki + checkout + Job honesty)

> **Status**: In Review
> **Created**: 2026-09-12
> **Spec Reference**: Bones marathon slice 1. Architect Done bars after grok @ c82ff5f (260+261+262 tip). One Homelab-class Ask → Wiki grounding + repo_file_* reads + Job honesty end-to-end. Claim only tool-provenanced facts. Live: Journey DONE; Observe same job_…; no invent. Do NOT start 264/265. Do NOT merge grok/qa/main.
> **Labels**: type:feat, P0, ControlPlane, Homelab, Honesty, Wiki, RepoTools, AntiTheatre, OutcomeSmoke
> **Branch**: `feat/homelab-outcome-smoke-263` (off grok @ c82ff5f; push feat only; never merge grok/qa/main)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. A Homelab-class outcome is one Ask that must **use the Wiki** and **read the AutoReiv checkout** in the same Job — not wiki-only theatre, not invent-about-code.
2. Example: summarize the AGENTS.md card rule into a Wiki note with a done-when the operator can open via `wiki_note_read`.
3. Jobs may claim **only tool-provenanced facts** (`wiki_note_*` and `repo_file_list` / `repo_file_read`). No invent.
4. Live on Jarvis→Ollama: Journey **DONE**; Observe the **same** `job_id`; Formulate→Execute.
5. This card is ONLY the Homelab-class outcome smoke. Do not start CARD-264/265. Do not merge grok/qa/main.

### Beat 2: What AutoReiv Does Now
1. CARD-260 fail-closes Wiki path claims; CARD-262 fail-closes checkout claims; CARD-261 freezes honesty/stress as a tip merge gate.
2. Homelab pack already lists `wiki_note_*` + `repo_file_list` / `repo_file_read`. Standing Chat already injects both grounding constraints.
3. No standing Homelab-class outcome smoke proves Wiki + repo + honesty + same `job_id` + Journey DONE together.

### Beat 3: What Will Change
1. Ready card + classifier that scores Homelab-class outcome bars (Wiki provenance + repo provenance + same `job_id` + Journey DONE + no invent).
2. Scripted live proof on Jarvis→Ollama via the Homelab agent (`notes/scripts/homelab_outcome_smoke_263.py`).
3. Artifact `notes/marathon-card263-live-smoke.json`; CHANGELOG; push feat tip only.

---

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-HLOS-001]**: One Homelab-class Ask uses Wiki grounding (`wiki_note_*`) AND checkout reads (`repo_file_list` / `repo_file_read`) in the same Job. (classifier + live script)
- [x] **[REQ-HLOS-002]**: Claims only tool-provenanced facts; invented Wiki or checkout paths fail the smoke (no invent).
- [x] **[REQ-HLOS-003]**: Formulate→Execute on the same `job_id`; Observe standing-journey for that same `job_id` shows Journey DONE. (classifier bars)
- [ ] **[REQ-HLOS-004]**: Live proof Jarvis→Ollama; artifact `notes/marathon-card263-live-smoke.json`. **PENDING Jarvis Shell** — executor box cannot reach :8000/Ollama; do not invent a job_id.
- [x] **[REQ-HLOS-005]**: Classifier tests red→green; `--validate` exit 0; feat pushed only — never qa/main; not merged to grok. Do not start 264/265. CHANGELOG [Unreleased] bullet still to fold on Jarvis (`notes/card263-changelog-snippet.md`).

## 3. Constraints

- Feat off grok @ c82ff5f (includes 260+261+262). Never qa/main. Never merge grok.
- Reuse standing Chat + catalog + CARD-260/262 grounding. Do not invent a second orchestrator.
- Homelab agent is the live actor. `memory.db` ≠ `storage.db`. Honesty. Quality > speed.
- TDD if new glue is needed; live integration smoke may be the primary deliverable if primitives already exist — card + scripted live proof required.

## 4. Modules Likely Touched

- `src/application/orchestration/homelab_outcome_smoke.py` (new classifier)
- `notes/scripts/homelab_outcome_smoke_263.py` (validate + live)
- `tests/unit/orchestration/test_card263_homelab_outcome_smoke.py` (new)
- `.github/cards/CARD-263-homelab-class-outcome-smoke.md`
- `CHANGELOG.md`, `notes/marathon-card263-live-smoke.json`

## 5. CoS smoke prompt

```
Homelab-class: Using repo_file_list and repo_file_read, read AGENTS.md from the AutoReiv checkout and summarize the card rule (Three Beats; cards stay Ready until build) into a new Wiki note in 00_Inbox. Done-when: I can open that note via wiki_note_read and the note only claims what repo_file_read returned. Do not invent checkout or wiki paths. Keep under 160 words.
```

```
python notes/scripts/homelab_outcome_smoke_263.py --validate
python notes/scripts/homelab_outcome_smoke_263.py --live
```

## 6. Marathon Build Lock

- Architect Done bars locked — Builder implements now.
- TDD where practical; live Jarvis→Ollama proof required.
- Do NOT merge to grok/qa/main. Do NOT start 264/265.

## 7. Marathon Build Notes

- **Tip**: `1bd7ef5` on `feat/homelab-outcome-smoke-263` (off grok @ `c82ff5f`). Not merged to grok/qa/main.
- **Validate**: `python notes/scripts/homelab_outcome_smoke_263.py --validate` exit 0 (fx_pass / fx_no_repo / fx_invent / fx_wrong_observe).
- **Unit**: 8 classifier tests green (pass + wiki-only fail + repo-only fail + observe mismatch + invent + not-DONE + missing Formulate/Execute + fixture pack).
- **Live**: NOT RUN. Executor Shell is box-bound; machineId `dadba06c-158d-4782-83a3-9e663c71e6c5` did not route. No invented job_id.
- **Jarvis pickup**: fetch feat, restart serve, `--live`, commit `notes/marathon-card263-live-smoke.json` + CHANGELOG snippet, mark Done.
- **Design-room**: One Homelab-class Ask grounds Wiki + repo_file_* on the same job_id; Journey DONE on Observe; claims only tool-provenanced facts — no invent.
- Stop — parent owns 264 and the Jarvis live run.

## Tip
- Live: job_1080eb9f4ab4 Journey DONE (Formulate+Execute); wiki+repo provenance; no invent.
