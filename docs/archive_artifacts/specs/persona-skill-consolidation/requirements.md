# Requirements Specification: Persona Skill Consolidation

> **Spec Status**: In Review  
> **Target Release**: Milestone 19  
> **Primary Component**: Agent Architecture & Skills Engine

---

## 1. Executive Summary & Intent
AutoReiv is evolving to a Single-Brain / Autonomic OS model where the primary companion (`AutoReiv Core`) dynamically pages capabilities as modular skill runbooks on demand, and `Direct Mode` is available for raw ungrounded chat. Separate agents are reserved exclusively for service accounts/daemons (`LIFECYCLE_MISMATCH`), security boundaries (`SECURITY_COLLISION`), or hardware isolation.

This specification governs absorbing the specialized personas (`developer`, `forge`, `tutor`) into compliant skill runbooks (`sdlc-engineering`, `agent-authoring`, `socratic-tutoring`) under `platform-packs/autoreiv/skills/`, retiring their standalone packs, and completely removing deprecated legacy profiles (`homelab` fleet and `finance`).

---

## 2. User Stories & EARS Functional Requirements

### [REQ-CONSOL-001]: Migration of Developer Persona to SDLC Engineering Skill
- **Type**: State-Driven
- **EARS Statement**: `WHILE AutoReiv executes software engineering, planning, or code verification tasks THE SYSTEM SHALL provide the sdlc-engineering skill runbook containing guidelines for read-only exploration, TDD, ADR/spec authoring, and cli_exec/execute_code execution with at most 6 declared tools.`
- **Acceptance Criteria**:
  - [ ] Given `platform-packs/autoreiv/skills/sdlc-engineering/SKILL.md`, it must declare valid YAML frontmatter with `requires_tools` of length <= 6 (e.g. `read_project_file`, `write_project_file`, `list_project_dir`, `cli_exec`, `execute_code`, `propose_followup`).
  - [ ] Given the runbook, it must include a testable `## Done-when` or `verification:` contract.

### [REQ-CONSOL-002]: Migration of Forge Persona to Agent Authoring Skill
- **Type**: State-Driven
- **EARS Statement**: `WHILE AutoReiv conducts capability architecture, tool synthesis, or training intake THE SYSTEM SHALL provide the agent-authoring skill runbook containing Socratic intake discovery, agent pack inspection, deliverable taxonomy recommendation, and training job dispatch with at most 6 declared tools.`
- **Acceptance Criteria**:
  - [ ] Given `platform-packs/autoreiv/skills/agent-authoring/SKILL.md`, it must declare valid YAML frontmatter with `requires_tools` of length <= 6 (e.g. `inspect_agent_pack`, `launch_factory_training`, `lookup_agents`, `handoff_to_agent`).
  - [ ] Given the runbook, it must include a testable `## Done-when` or `verification:` contract.

### [REQ-CONSOL-003]: Migration of Tutor Persona to Socratic Tutoring Skill
- **Type**: State-Driven
- **EARS Statement**: `WHILE AutoReiv conducts educational dialogues, Feynman conceptual challenges, or active recall testing THE SYSTEM SHALL provide the socratic-tutoring skill runbook grounded in wiki notes with at most 6 declared tools.`
- **Acceptance Criteria**:
  - [ ] Given `platform-packs/autoreiv/skills/socratic-tutoring/SKILL.md`, it must declare valid YAML frontmatter with `requires_tools` of length <= 6 (e.g. `wiki_note_read`, `wiki_note_search`, `wiki_note_list`, `list_wiki_templates`).
  - [ ] Given the runbook, it must include a testable `## Done-when` or `verification:` contract.

### [REQ-CONSOL-004]: Platform Seed Pack Retirement & Legacy Alias Mapping
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL restrict PLATFORM_PACK_IDS to ("autoreiv", "direct"), add ("developer", "tutor", "forge") to RETIRED_PLATFORM_PACK_IDS, clean retired folders from user data on startup, delete platform-packs/{developer,forge,tutor}, and alias legacy agent IDs developer, tutor, forge to autoreiv.`
- **Acceptance Criteria**:
  - [ ] Given repo `platform-packs/`, only `autoreiv` and `direct` remain.
  - [ ] Given `cleanup_orphaned_platform_packs()`, any existing `developer`, `tutor`, or `forge` folders in user data are pruned.
  - [ ] Given `canonical_agent_id()`, requests for `developer`, `tutor`, or `forge` return `autoreiv`.

### [REQ-CONSOL-005]: Total Purge of Deprecated Homelab and Finance Profiles
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL delete all homelab fleet profiles (coordinator, architect, engineer, admin, janitor) from profiles.py, delete homelab recipes and outcome smoke scripts, and delete obsolete homelab/finance tests.`
- **Acceptance Criteria**:
  - [ ] Given `src/domain/agents/profiles.py`, zero `HOMELAB_*` constants or functions exist.
  - [ ] Given `src/application/orchestration/`, `homelab_domain_recipe.py` and `homelab_outcome_smoke.py` are deleted.
  - [ ] Given `tests/`, dedicated homelab and finance unit/integration test files are removed.

### [REQ-CONSOL-006]: Mechanical Capability Linter Compatibility
- **Type**: Event-Driven
- **EARS Statement**: `WHEN autoreiv lint-skills executes THE SYSTEM SHALL resolve user and platform data directories cleanly without import errors and report zero validation errors across all bundled skills.`
- **Acceptance Criteria**:
  - [ ] Given `src/application/skills/linter.py`, `resolve_live_data_root` is correctly imported and invoked.
  - [ ] Given `python -m src.cli.main lint-skills`, the process exits with code 0 and all bundled skills pass.

---

## 3. Non-Functional & Boundary Constraints
- **Cognitive Budget**: Every skill runbook must respect `MAX_TOOLS_PER_SKILL = 6` and `MAX_RUNBOOK_BODY_CHARS = 8000`.
- **Regression Safety**: All core tests in `tests/` must pass with zero regression.
- **Single-Brain Invariant**: Core cognitive memory stays in `autoreiv_memory.db`.

---

## 4. Out of Scope
- Re-architecting Agent Training Factory 8-phase pipeline (Factory continues to synthesize tools and skills into target packs).
- Re-introducing new homelab MCP servers or finance integrations (deferred to future cards).
