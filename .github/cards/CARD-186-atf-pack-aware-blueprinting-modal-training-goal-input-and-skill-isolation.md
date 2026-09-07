# [CARD-186] ATF Pack-Aware Blueprinting Modal Training Goal Input and Skill Isolation

> **Status**: Ready
> **Created**: 2026-09-07
> **Spec Reference**: none
> **Labels**: `type:feature`, `agent-training-factory`, `agent-packs`

---

## 1. Why / Intent
When training an existing agent (such as `Personal Finance Lead`), the Agent Training Factory should build upon the agent's existing skills, tools, and storage rather than generating duplicate generic stubs.

Three specific flaws lead to poor training outputs and UI clutter:
1. **Invisible Seed Intent**: The training modal lacks an explicit Goal / Intent input field. When opened from Agent Studio without existing chat prompt text, the frontend silently sets `seedIntent = "Train capabilities for <agent_id>"`. This synthesized string pollutes the runbook title, scope, and objectives.
2. **Pack Amnesia in Blueprint**: The `BlueprintPhase` does not inspect the agent's existing pack (`pack.json`), leaving it blind to existing skills (e.g. `personal_finance`), existing tools (`log_transactions`, `manage_budget`, etc.), and private SQLite storage (`finance_storage.db`). When the LLM falls back, it defaults to creating a redundant `{agent_id}` skill and a dummy `manage_{agent_id}` dispatcher tool with service actions (`status`, `restart`).
3. **Pack Skill Global Leak**: During pack promotion or import, `AgentPackService._copy_skills_in()` copies private agent pack skills into `$DATA_DIR/skills/`, causing pack-specific skills to leak into the global platform skills catalog and runbook editor.

---

## 2. What to Build
- **Train Agent Modal Visible Goal Input (`src/web/templates/index.html`, `src/web/static/modules/studios/chat.js`)**:
  - Add a visible `#trainSeedIntentInput` field ("Training Goal & Intent") in `#trainAgentHandshakeModal`.
  - When opening the modal for an existing agent, pre-populate this field with the agent's description or allow operator editing.
  - If left blank, derive the goal from the first line of the objectives instead of hardcoding `"Train capabilities for <agent_id>"`.
- **Existing Pack Grounding in Blueprint (`src/application/agent_training_factory/phases/blueprint.py`)**:
  - In `BlueprintPhase.run`, inspect `packs/<agent_id>/pack.json` (or the agent profile in registry) if the target agent already exists.
  - Extract existing skills, existing tools, and storage configuration, and pass them into the LLM blueprint prompt and heuristic fallback.
  - When formulating the blueprint for an existing agent, ensure new tools are mapped to existing skills (e.g., adding analytics/forecasting tools into `personal_finance`) or grouped into a genuinely distinct domain skill (e.g. `financial-analytics`), preventing duplicate `{agent_id}` skills or generic `manage_{agent_id}` dummy dispatchers.
- **Database / Analytics Tool Synthesis Heuristics (`src/application/orchestration/tool_synthesizer.py`)**:
  - For agents with SQLite storage or data/analytics objectives, generate meaningful domain tool stubs (querying, reporting, aggregating) rather than an empty OS-service dispatcher (`status`, `start`, `stop`, `restart`).
- **Private Pack Skill Isolation (`src/application/agent_packs/service.py`)**:
  - In `AgentPackService._import_folder()`, do NOT copy pack skills from `packs/<agent_id>/skills/` into the global `$DATA_DIR/skills/` directory. Private agent pack skills must remain encapsulated within their respective pack directory.
  - Ensure the runbook editor endpoint (`GET /api/skills/user-packs/{pack_id}`) can look up pack-owned runbooks directly from `packs/<agent_id>/skills/<skill_id>/SKILL.md` if not present in the global catalog.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] **AC-1**: `#trainAgentHandshakeModal` includes a visible `#trainSeedIntentInput` field; if left blank, it derives the intent from the first objective instead of injecting `"Train capabilities for <slug>"`.
- [ ] **AC-2**: When training an existing agent, `BlueprintPhase` reads `pack.json` and incorporates existing skills, tools, and storage into the blueprint prompt and heuristic fallback.
- [ ] **AC-3**: `BlueprintPhase` does not emit a duplicate skill named `{agent_id}` or a generic `manage_{agent_id}` tool when the target agent already has domain skills.
- [ ] **AC-4**: Promoting or importing an agent pack does NOT copy private pack skills into `$DATA_DIR/skills/`.
- [ ] **AC-5**: The runbook editor can view and edit private pack runbooks under `packs/<agent_id>/skills/`.
- [ ] **AC-6**: Automated unit tests pass via `pytest tests/unit/agent_training_factory/`.
- [ ] **AC-7**: Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Working on branch `qa`.
- Card stays **Ready** until human visionary approves and says build.
- Follow AGENTS.md "How we walk cards with Jacob" (three beats: What he means, What AutoReiv does now, What will change).
