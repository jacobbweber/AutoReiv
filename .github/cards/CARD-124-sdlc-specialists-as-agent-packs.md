# [CARD-124] SDLC specialists as Agent Packs

> **Status**: Done
> **Created**: 2026-08-31
> **Spec Reference**: CARD-119; CARD-082; CARD-083; CARD-084; CARD-117; CARD-118; CARD-120; CARD-121; CARD-123
> **Labels**: `type:feat`, `type:docs`

---

## 1. Why / Intent
**Shipped core is Assistant + AutoReiv.** Conductor, Coding, and Review are specialists, not forever-builtins. An Agent Pack is always **one agent** (many skills and tools). The SDLC trio is **three packs**, not one team zip.

**Walked (2026-08-31 Jacob t185u-t192u):** Convert the three Python builtins into three Agent Packs. Drop those profiles from core so a fresh install does not get a second Conductor. Repo root `agent-packs/` is an optional catalog (not loaded on startup). README says import is optional. On Jacob's running app, this card also imports the three into `$DATA_DIR/packs/` so they are already there. Later packs he authors belong in `agent-packs/` when they should live in git.

This is a **product card**. Do not implement until Jacob says build. Do not name inspiration products.

---

## 2. What to Build

- Three pack folders in the repo: `agent-packs/conductor/`, `agent-packs/coding/`, `agent-packs/review/`. Schema **1.1** (tools nested under skills). Same catalog tools as today, ticked on the pack. No new Python tool modules in the pack zip.
- `agent-packs/README.md`: these packs exist; Import is optional; a fresh AutoReiv is Assistant + AutoReiv until you import. Root `README.md` points at that folder.
- Drop `CONDUCTOR_PROFILE`, `CODING_PROFILE`, and `REVIEW_PROFILE` from shipped builtins (`src/domain/agents/profiles.py` and the builtin map). **Do not** rip Agent Builder (it stays a hidden builtin: Chat/Studio skip `agent-builder` by id).
- Do **not** auto-load `agent-packs/` on startup. Import is Agent Studio Import / AutoReiv `import_agent_pack` / this card's one-time install into Jacob's `$DATA_DIR/packs/`.
- On Jarvis, after the packs exist: import the three into `$DATA_DIR/packs/` so Agent Studio lists them and Chat can pick Conductor. Coding and Review have **Show in Chat** off.
- Tests that assumed those three were builtins must load them as packs (or fixtures). Local commit only. No push.

### Conductor pack (`id="conductor"`)
- **Job:** Jacob talks to this one. Writes cards and specs. Hands one Ready card to Coding. Asks Jacob when a card is still Discuss or review rounds are maxed. Does not code. Does not edit product files.
- **Instructions (identity text):** the walk we locked. One primitive at a time. Three beats: what he means, what AutoReiv does now, what will change. Stop if a word disagrees before anyone touches code. Real technical name, then the screen or file. Cards stay Ready until he says build. Extract intent when he over-explains.
- **Show in Chat:** on.
- **Skills (runbooks):**
  - `covision-card` — walk a card with Jacob, write card + spec, park Ready.
  - `handoff-coding` — one Ready card to Coding; on Review fail under max rounds, send the same card back to Coding; at max rounds, ask Jacob.
- **Tools (existing catalog):** `list_cards`, `read_card`, `write_card`, `set_card_status`, `read_spec`, `write_spec`, `read_steering`, `list_project_dir`, `read_project_file`, `handoff_to_agent`, `lookup_agents`, `propose_followup`. No `write_project_file`. No `execute_code`. No `cli_exec`.

### Coding pack (`id="coding"`)
- **Job:** one Ready card. Implement against the spec. Conventional commit if a repo exists. Set In Review. Stop. Do not mark Done or Returned. Do not start another card. Do not do AutoReiv platform / `cli_exec`.
- **Show in Chat:** off. Handoff can still target `coding`. Agent Studio still lists it.
- **Skills (runbooks):**
  - `implement-one-card` — read card/spec, write the deliverable, commit if repo, In Review, stop.
- **Tools (existing catalog):** `execute_code`, `handoff_to_agent`, `read_card`, `read_spec`, `set_card_status`, `list_project_dir`, `read_project_file`, `write_project_file`, `git_status`, `git_diff`, `git_branch`, `git_commit`.

### Review pack (`id="review"`)
- **Job:** judge Coding's result. Never writes product files. Returns a concrete fix list, then hands off to Coding (fix it) or Conductor (intent is still unclear).
- **Show in Chat:** off. Handoff can still target `review`.
- **Skills (runbooks):**
  - `spec-review` — Pass: Done. Fail: Returned with the missing requirement named. Spec/card only.
  - `code-review` — diff, syntax, quality, `AGENTS.md` / steering standards. Concrete fix list. No file writes.
  - `alignment` — does the diff match what was locked (including UI click to the function). If the card is still mushy, hand off to Conductor.
- **Tools (existing catalog):** keep `list_cards`, `read_card`, `read_spec`, `read_steering`, `list_project_dir`, `read_project_file`, `set_card_status`, `handoff_to_agent`, `lookup_agents`. **Add** `git_diff`, `git_status`. **Do not** tick `write_project_file` or `git_commit`. Do not tick `execute_code` on this card (test-running is later if Jacob asks).

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `agent-packs/conductor`, `agent-packs/coding`, `agent-packs/review` exist as schema 1.1 packs with the skills and tool ticks above.
- [x] `agent-packs/README.md` and a root README pointer: optional import; fresh install is Assistant + AutoReiv.
- [x] `profiles.py` no longer registers Conductor, Coding, or Review as builtins. Agent Builder stays (hidden).
- [x] Startup does not scan `agent-packs/` into the roster. Import is explicit.
- [ ] Live: Jacob's `$DATA_DIR/packs/` has the three imported. Chat `#agentSelect` shows Conductor, not Coding or Review. Agent Studio left list shows all three. Handoff still resolves `coding` and `review`. (data-dir import is done on implement; Chat/Studio live-test stays for Jacob)
- [x] Conductor instructions contain the locked walk language (three beats, stop on a disagreeing word, Ready until build).
- [x] Review never has write/commit tools. Fail path is a concrete list + handoff to Coding or Conductor.
- [x] Unit/vitest updated. Status **In Review** after code. Not Done until live test. Local commit only. No push.

---

## 4. Constraints & Honor Flags
- Work on `qa`. Do not push. Do not clone.
- Pack = one agent. No team zip. Folder name is `agent-packs` (not packets).
- Do not reverse CARD-117/121: Chat still lists that agent's ticked tools every turn.
- Do not put Python tool implementations in the pack. Existing catalog only.
- Do not auto-load the repo catalog on startup.
- Do not rip Agent Builder internals / skill-curator retarget unless a later lock says so.
- Do not start CARD-116 or CARD-122.
- Do not invent Echo-style demo Python tools.
- AutoReiv `scaffold_agent_pack` still writes `$DATA_DIR/packs/`. This card does not make every scaffold dirty the git tree. Packs that belong in git are copied into `agent-packs/` (this card does that for the three).

---

## 5. Out of scope
- Per-agent memory (CARD-116).
- CARD-122 three-beats SKILL.md as a generic coder+visionary pack (Conductor instructions on this card already carry that walk).
- Named observability skill on AutoReiv.
- Review running tests via `execute_code`.
- Ripping Agent Builder.
- Pack-builder that writes new Python tool modules.
- GitHub issue sync (CARD-088) and CARD-079 push.

---

## 6. Walked lock (2026-08-31)

| Beat | Lock |
|------|------|
| Pack shape | Always one agent, many skills/tools. Three packs, not one team bundle (t186u). |
| Conductor | Same job as today's builtin. Instructions = this walk (t187u). |
| Coding | One Ready card, implement, In Review, stop (t188u). |
| Review | Spec + code quality + alignment. Never writes files. Concrete list, then Coding or Conductor (t189u). |
| Chat | Conductor on. Coding and Review off. Handoff still works (t190u). |
| Fresh install | Assistant + AutoReiv only. Catalog is `agent-packs/`. Jacob's app gets them imported on this card (t191u-t192u). |

---

## 7. Pickup
Say **build** / **continue**. Then implement on Jarvis `qa`, local commit, no push, status In Review, Jacob live-tests.
