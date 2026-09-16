# [CARD-341] Platform Agent Decoupling: Assistant & Wiki Retirement, Tutor Education Pinning & Roster Consolidation

> **Status**: In Review
> **Created**: 2026-09-16
> **Spec Reference**: docs/adr/0052-skill-and-tool-scoping-and-specialist-dispatch.md
> **Labels**: `type:refactor`, `domain:agents`, `domain:skills`, `domain:education`

---

## 1. Why / Intent

In CARD-339, AutoReiv introduced dynamic skill and tool scoping and consolidated the front-of-house chat pickers. However, `assistant`, `developer`, and `wiki` were only visually hidden in the UI. Their underlying pack manifests remain on disk, and core backend services still anchor defaults to legacy agent IDs (e.g. Education Studio defaulting `agent_id="assistant"`).

Jacob analyzed the memory and database boundaries:
- **Tools are not the reason to split agents**—CARD-339 dynamic scoping already eliminates tool schema overhead on cold turns.
- **Memory and cognitive role isolation is the true architectural boundary**:
  - **Education (`tutor`)**: Educational course mastery, flashcards, SM-2 retention intervals, and Socratic dialogues must remain isolated in `tutor_memory.db`. Pinned to `autoreiv`, educational quiz state would pollute general SRE and platform episodic recall.
  - **Software Engineering (`developer`)**: Coding, TDD loops, git hygiene, and spec-driven workflows represent a focused engineering role bound to Projects Studio, isolated in `developer_memory.db`.
  - **Daily Operations & Wiki (`autoreiv`)**: General companion work, daily tasks, weekly review notes, and wiki vault curation belong naturally to `autoreiv`. `assistant` and `wiki` are redundant as standalone agent packs.

### The Three Beats
1. **What Jacob means**:
   Permanently decouple and delete `assistant` and `wiki` from AutoReiv's codebase, manifest registries, and disk storage (`platform-packs/` and `%LOCALAPPDATA%\AutoReiv\packs/`). Fully migrate daily task tracking and wiki curation into `autoreiv`'s modular skills. Formally pin Education Studio to `tutor`, and preserve `developer` as the dedicated software engineering specialist for Projects Studio.
2. **What AutoReiv does now**:
   - **UI Hiding Only**: `CHAT_HIDDEN_BY_ID` hides `assistant`, `developer`, and `wiki`, but all packs still exist on disk and are auto-seeded on boot.
   - **Hardcoded Legacy Defaults**:
     - `src/web/routers/education.py`: 14 endpoints default `agent_id="assistant"`, writing learner mastery into `assistant_memory.db` instead of `tutor_memory.db`.
     - `src/cli/main.py`: CLI chat defaults to `agent_id="assistant"`.
     - `src/domain/wiki/frontmatter.py` & `store.py`: Default note author metadata is `"assistant"`.
     - `src/application/routines/manifests.py`: Built-in routines default to `"assistant"` or `"wiki"`.
     - `src/application/agent_packs/schema.py` & `src/infrastructure/skills/platform_packs.py`: `PLATFORM_PACK_IDS` includes `assistant` and `wiki`.
   - **Capability Gaps on `autoreiv`**: `autoreiv` does not yet declare all weekly task tools (`get_or_create_weekly_note`, `log_daily_work_item`, `complete_weekly_task`, `rollover_weekly_tasks`, `get_weekly_summary`) in its manifest.
3. **What will change**:
   - **Platform Agent Roster Solidified (4 Packs)**:
     1. **`autoreiv`**: Primary Companion, SRE, Daily Coordinator, and Wiki Curator (absorbs `assistant` tasks and `wiki` curation).
     2. **`developer`**: Dedicated Software Engineer (owns Projects Studio, coding jobs, and `developer_memory.db`).
     3. **`tutor`**: Dedicated Education Specialist (owns Education Studio, course mastery, and `tutor_memory.db`).
     4. **`direct`**: Zero-tool baseline for model benchmarking and pure chat.
   - **Capability Migration to `autoreiv`**:
     - Declare all weekly task tools and wiki curation tools in `platform-packs/autoreiv/pack.json`.
     - Dynamic scoping activates `tasks` and `wiki` tools on-demand when activated.
   - **Subsystem Decoupling**:
     - `src/web/routers/education.py`: Re-anchor default `agent_id` from `"assistant"` to `"tutor"`.
     - `src/cli/main.py`: Update default CLI agent to `"autoreiv"`.
     - `src/domain/wiki/frontmatter.py` & `store.py`: Update default author to `"autoreiv"`.
     - `src/application/routines/manifests.py`: Rebind default routines to `"autoreiv"`.
     - `src/application/agent_packs/schema.py`: Update `PLATFORM_PACK_IDS` to `("autoreiv", "developer", "tutor", "direct")`.
     - `src/infrastructure/skills/platform_packs.py`: Prune seed list and add startup cleanup for orphaned `$DATA_DIR/packs/{assistant,wiki}`.
   - **Disk Deletion**:
     - Delete `platform-packs/assistant` and `platform-packs/wiki` from repository checkout.
     - Delete `%LOCALAPPDATA%\AutoReiv\packs\{assistant,wiki}` from user data.
   - **Test Suite Modernization**:
     - Migrate unit and integration tests from `"assistant"` / `"wiki"` to `"autoreiv"` or `"tutor"`.

---

## 2. What to Build

### 1. Capability Migration to `autoreiv`
- **Update `platform-packs/autoreiv/pack.json`**:
  - Add weekly task tools to `pack_tool_names`:
    `get_or_create_weekly_note`, `log_daily_work_item`, `complete_weekly_task`, `rollover_weekly_tasks`, `get_weekly_summary`.
  - Ensure wiki curation tools are in `pack_tool_names`:
    `wiki_note_create`, `wiki_note_read`, `wiki_note_update`, `wiki_note_search`, `wiki_note_list`, `wiki_note_organize`, `list_wiki_templates`, `wiki_overview`, `wiki_graph`, `promote_artifact_to_wiki`.
  - Add `tasks` and `wiki` to `skills` and `allowed_skill`.
- **Verify Skills in `platform-packs/autoreiv/skills/`**:
  - `tasks/SKILL.md` documents weekly notes, task logging, and rollovers.
  - `wiki/SKILL.md` documents wiki search, note creation, templates, and inbox organization.
- **Update `DYNAMIC_SKILL_TOOLS` in `src/application/agent_packs/schema.py`**:
  - Ensure `tasks` and `wiki` dynamic skill mappings cover all migrated tools so dynamic tool scoping mounts them seamlessly.

### 2. Backend Subsystem Decoupling
- **Education Subsystem** (`src/web/routers/education.py` & `src/web/routers/education_priming.py`):
  - Change default `agent_id: str = "assistant"` to `agent_id: str = "tutor"`.
  - Ensure all learner ledgers, course mastery, and spaced repetition operations execute strictly against `tutor_memory.db`.
- **CLI Entrypoint** (`src/cli/main.py`):
  - Change default agent from `"assistant"` to `"autoreiv"`.
- **Wiki Domain Defaults** (`src/domain/wiki/frontmatter.py`, `src/domain/wiki/store.py`):
  - Change default note author from `"assistant"` to `"autoreiv"`.
- **Routine Manifests** (`src/domain/routines/manifests.py`):
  - Rebind routine definitions previously attached to `"assistant"` or `"wiki"` to `"autoreiv"`.
- **Job Phase Orchestrator** (`src/application/orchestration/job_phase_orchestrator.py`):
  - Maintain coding execution phases routed to `"developer"`.
  - Route wiki curation and task phases to `"autoreiv"`.
- **Platform Pack Registry & Auto-Cleanup**:
  - `src/application/agent_packs/schema.py`:
    - Set `PLATFORM_PACK_IDS = frozenset({"autoreiv", "developer", "tutor", "direct"})`.
    - Update `CHAT_SHOWN_BY_ID = frozenset({"autoreiv", "developer", "direct"})`.
    - Remove `developer` from `CHAT_HIDDEN_BY_ID`.
  - `src/infrastructure/skills/platform_packs.py`:
    - Set `PLATFORM_PACK_IDS = ("autoreiv", "developer", "tutor", "direct")`.
    - Add startup auto-cleanup to delete stale user-data pack folders: `$DATA_DIR/packs/assistant` and `$DATA_DIR/packs/wiki`.

### 3. Disk Deletion
- Delete from git working tree:
  - `platform-packs/assistant/`
  - `platform-packs/wiki/`
- Prune from local user data directory:
  - `%LOCALAPPDATA%\AutoReiv\packs\assistant\`
  - `%LOCALAPPDATA%\AutoReiv\packs\wiki\`

### 4. Test Suite Refactoring
- Update unit tests in `tests/unit/` asserting on `"assistant"` or `"wiki"`:
  - Education tests -> assert `agent_id="tutor"`.
  - Daily tasks / CLI / general tests -> assert `agent_id="autoreiv"`.
  - Verify all unit and integration tests pass cleanly.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `autoreiv` declares all daily task tools and wiki curation tools in `pack.json`.
- [x] Activating `tasks` or `wiki` skills on `autoreiv` dynamically scopes the correct tools.
- [x] `src/web/routers/education.py` defaults to `agent_id="tutor"`, isolating all education mastery in `tutor_memory.db`.
- [x] `src/cli/main.py` defaults to `agent_id="autoreiv"`.
- [x] Wiki frontmatter defaults author to `"autoreiv"`.
- [x] Routine manifests rebind default routines to `"autoreiv"`.
- [x] `PLATFORM_PACK_IDS` in `schema.py` and `platform_packs.py` consists solely of `autoreiv`, `developer`, `tutor`, `direct`.
- [x] `platform-packs/assistant` and `platform-packs/wiki` are completely deleted from the git repository.
- [x] `%LOCALAPPDATA%\AutoReiv\packs\{assistant,wiki}` are removed from user data.
- [x] `developer` is fully operational in Projects Studio and Chat Studio without regressions.
- [x] `tutor` is fully operational in Education Studio without regressions.
- [x] All backend unit tests (`pytest tests/unit/`) pass with zero regressions.
- [x] All frontend unit tests (`npm run test:unit:frontend`) and linters (`npm run lint:frontend`) pass with zero errors.
- [x] Serve restarts cleanly and live smoke test confirms all 4 platform agents behave as expected.

---

## 4. Constraints & Honor Flags

- **Zero remote push**: Do not push to origin or any remote.
- **Card-first invariant**: No implementation code without Jacob's explicit `build` instruction.
- **Single active card**: CARD-341 is the sole active card during this refactoring.
- **Branch hygiene**: Cut isolated branch `feat/CARD-341-platform-agent-decoupling-and-disk-cleanup` from `qa`.
