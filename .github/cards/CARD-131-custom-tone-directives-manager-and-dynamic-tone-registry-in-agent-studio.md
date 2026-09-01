# [CARD-131] Custom Tone Directives Manager and Dynamic Tone Registry in Agent Studio

> **Status**: In Review
> **Created**: 2026-08-31
> **Spec Reference**: CARD-003; CARD-016; CARD-050
> **Labels**: `type:feat`, `type:ui`, `type:agents`

---

## 1. Why / Intent
Users want the flexibility to define, customize, and refine agent conversational personas without being constrained to 6 static built-in tones. By introducing a first-class Dynamic Tone Registry and a "Manage Tones" modal in Agent Studio, users can create specialized tone directives (e.g., Executive Briefing, Code Reviewer, ELI5, Socratic Tutor), edit directive prompts, and delete custom presets directly from the agent editing workflow.

---

## 2. Visual Contract & ASCII Wireframes

### Agent Studio - Persona Modulation (Card 3)
```text
+--------------------------------------------------------------------------+
| 🎭 Persona & Execution Bounds                                            |
|                                                                          |
| Tone Preset                             [ ⚙️ Manage Tones ]              |
| [ Technical (Precise, authoritative, code-focused)                  v ]  |
|                                                                          |
| Max Turns per Turn Loop: [ 10 ]                                          |
| Chat session cleanup (days): [ 30 ]                                      |
+--------------------------------------------------------------------------+
```

### Manage Tones Modal (`#manageTonesModal`)
```text
+--------------------------------------------------------------------------+
| 🎭 Manage Tone Directives                                          [ ✕ ] |
+--------------------------------------------------------------------------+
| Create, edit, and organize custom tone directives for agent personas.    |
|                                                                          |
| ACTIVE TONES                                           [ + New Tone ]    |
| ------------------------------------------------------------------------ |
| • Default (Balanced conversational)                           [Built-in] |
|   "Standard helpful, conversational baseline."                           |
|                                                                          |
| • Technical (Precise, authoritative)                          [Built-in] |
|   "Tone directive: Technical, precise, and authoritative."               |
|                                                                          |
| • Executive Briefing                                            [Custom] |
|   "Tone directive: High-level brevity. Lead with bottom line."           |
|                                                     [ ✏️ Edit ] [ 🗑️ Del ] |
| ------------------------------------------------------------------------ |
|                                                                          |
| [ + NEW TONE / EDIT TONE FORM ]                                          |
| Name / Label : [ Executive Briefing                                    ] |
| Slug / ID    : [ executive_briefing                                    ] |
| Directive    : [ Tone directive: High-level executive brevity. Lead    ] |
|                [ with the bottom-line metrics, 3 bullets, and 1 action. ] |
|                                                                          |
|                                             [ Cancel ]  [ Save Tone ]    |
+--------------------------------------------------------------------------+
```

---

## 3. What to Build

### Slice 1: Domain & Storage Layer
- Define `ToneDefinition` model (`id: str`, `name: str`, `description: str`, `directive: str`, `is_builtin: bool = False`) in `src/domain/kernel/models.py`.
- Update `AgentTone` / `AgentProfile.tone` to allow string-based dynamic tone IDs while preserving enum values as built-in defaults.
- Create SQLite table `tones` in `src/infrastructure/memory/repositories/tones.py` seeded with the 6 built-in presets (*default, technical, concise, friendly, academic, socratic*).
- Support loading custom tones from SQLite with fallback to built-ins.

### Slice 2: REST Endpoints
- `GET /api/tones`: Returns list of all available tones (built-in + custom).
- `POST /api/tones`: Creates a new custom tone (validates slug uniqueness, non-empty directive, rejects overriding built-in IDs).
- `PUT /api/tones/{tone_id}`: Updates name, description, and directive for a custom tone (built-in tones are read-only).
- `DELETE /api/tones/{tone_id}`: Deletes a custom tone (rejects deleting built-ins).

### Slice 3: Agent Kernel Dynamic Prompt Injection
- Update `AgentProfile.get_effective_system_prompt()` and `AgentKernel` prompt assembly to resolve tone directives dynamically from the state store when an agent uses a custom tone ID.

### Slice 4: Frontend Modal & Select Integration
- Add `[ ⚙️ Manage Tones ]` button to Card 3 in `src/web/templates/index.html`.
- Add `#manageTonesModal` in `index.html` with tone list and create/edit form.
- In `src/web/static/modules/studios/forge.js`:
  - Fetch `/api/tones` and dynamically populate `#forgeToneSelect`.
  - Wire up `#manageTonesBtn` to open modal, list tones, create new tone, edit custom tone, and delete custom tone.
  - Refresh `#forgeToneSelect` dynamically when tones are modified.

---

## 4. EARS Requirements & Acceptance Criteria

- `[REQ-TONE-001]` **Dynamic Tone Storage**: When the system initializes, the state store shall ensure built-in tone records exist and persist user-created tones in SQLite table `tones`.
- `[REQ-TONE-002]` **Tone REST API**: When a client sends a request to `/api/tones`, the backend shall support listing, creating, updating, and deleting custom tones.
- `[REQ-TONE-003]` **Built-in Protection**: While managing tones, the backend and UI shall prohibit modifying or deleting built-in system tones.
- `[REQ-TONE-004]` **Dynamic Prompt Resolution**: When an agent executes a turn, the agent kernel shall inject the resolved tone directive matching the agent's selected tone ID.
- `[REQ-TONE-005]` **Agent Studio UI Integration**: When a user clicks "Manage Tones" in Agent Studio, a modal shall open allowing CRUD operations and immediately sync the dropdown options upon save.
- [x] All automated unit & integration tests pass cleanly via `pytest`.
- [x] Frontend vitest tests pass cleanly.
- [x] Zero lint errors via `ruff check .`.
- [x] Local commit on `qa`. Card status `In Review` after code.

---

## 5. Constraints
- Work on `qa`. Do not push or tag unless explicitly asked.
- Zero breaking changes to existing agent profiles or built-in presets.
- Single card in focus.
