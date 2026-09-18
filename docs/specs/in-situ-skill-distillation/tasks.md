# Implementation Tasks: In-Situ Skill Distillation

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-SKIL-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Backend Distillation Service & Pack Adoption (`[REQ-SKIL-010]`, `[REQ-SKIL-013]`, `[REQ-SKIL-014]`)
- [x] **Task 1.1**: [RED] Write failing unit tests in `tests/unit/skills/test_skill_distillation_service.py` covering:
  - Extracting turn history from state store given session and message IDs.
  - Analyzing procedural friction vs. missing native tool requirement (`needs_tool`).
  - Synthesizing standardized `SKILL.md` (< 60 char description, proper sections).
  - Adopting skill: writing to `$DATA_DIR/packs/<agent>/skills/<slug>/SKILL.md` and updating target pack manifest.
- [x] **Task 1.2**: [GREEN] Implement `SkillDistillationService` in `src/application/skills/distillation_service.py`.
- [x] **Task 1.3**: [REFACTOR] Ensure clean isolation, safe fallback when LLM is unavailable, and zero git-checkout path writes.

### Slice 2: Web API Endpoints (`[REQ-SKIL-010]`, `[REQ-SKIL-013]`)
- [x] **Task 2.1**: [RED] Write failing router tests in `tests/unit/web/test_skills_distill_router.py` for `POST /api/skills/distill` and `POST /api/skills/adopt`.
- [x] **Task 2.2**: [GREEN] Implement FastAPI endpoints in `src/web/routers/skills.py` (or `agents.py`).

### Slice 3: Frontend Chat Studio Teaching Trigger, Modal, & Proposal Card (`[REQ-SKIL-011]`, `[REQ-SKIL-012]`, `[REQ-SKIL-014]`)
- [x] **Task 3.1**: [RED] Write failing frontend tests in `tests/unit/frontend/skill_distillation_ui.test.js` verifying:
  - Rendering `[ 💡 Teach Agent ]` action button on assistant messages.
  - Opening guidance modal and extracting optional guidance.
  - Rendering inline `.skill-proposal-card` with plain summary and accordion preview.
  - One-click adopt action and Factory Studio escalation action.
- [x] **Task 3.2**: [GREEN] Add modal markup in `src/web/templates/index.html` and wire logic in `src/web/static/modules/studios/chat.js`.
- [x] **Task 3.3**: Bump frontend cache-buster in `src/web/templates/index.html`.

### Slice 4: Verification, RTM Synchronization, & Pre-flight Gates
- [x] **Task 4.1**: Register `REQ-SKIL-010` through `REQ-SKIL-014` in `docs/rtm.json`.
- [x] **Task 4.2**: Run complete preflight gate suite (`npm run preflight`).
- [x] **Task 4.3**: Update `CHANGELOG.md` under `[Unreleased]` and update [CARD-352](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-352-in-situ-skill-workshop-learn-distillation-from-chat.md) to `In Review`.

