---
id: CARD-694
title: "Align product concepts, docs, and findings with M26-M28 for v1.1.0"
type: bug
status: Done
priority: P2
milestone: M28
needs_decision: none
proof:
  journeys: [card-694-housekeeping-and-1-1-prep]
  checks: [tests/unit/architecture/test_card694_docs_and_concepts_alignment.py, tests/unit/web/test_card686_retired_names_server.py, tests/unit/kernel/test_card680_product_concepts.py]
branch: feat/card-694-housekeeping-and-1-1-prep
log: {minutes: 35, qa_runs: 1, findings: 5}
created: 2026-10-16
completed: 2026-10-16
---

# CARD-694 Align product concepts, docs, and findings with M26-M28 for v1.1.0

## Problem
After M26–M28 retired `Skill Studio`, `Tools Studio`, `Architect`, `Developer`, and `Toolsmith` into the unified **Capabilities** studio (`#view-capabilities`) and the 3-agent roster (`AutoReiv`, `Tutor`, `Direct`):
1. `AUTOREIV_CONCEPTS` in `src/domain/agents/product_concepts.py` (injected into every agent's system prompt) still tells every agent `Shipped agents: AutoReiv, Developer, Tutor, Architect, Toolsmith, Direct.` and omits the **Capabilities** studio.
2. `docs/user-guide.md`, `steering/product.md`, `steering/structure.md`, and `steering/self-development.md` still describe `Skill Studio`, `Tools Studio`, `Architect`, `Developer`, and `Toolsmith` as current studios and shipped agents.
3. `docs/findings.md` still carries 31 lines for bugs already fixed and Done (`CARD-527`, `CARD-615`–`CARD-631`, `CARD-657`, `CARD-663`–`CARD-665`, `CARD-676`, `CARD-692`, `CARD-693`) or deleted `platform-packs/developer` and `Toolsmith` files.
4. Full release suite (`preflight.py --release`) had un-updated assertions from `CARD-692`/`CARD-693` (retired agents `developer`/`architect`/`toolsmith`, dock tabs `#tab-skill-studio`/`#tab-tools-studio`) plus POSIX path handling and skill frontmatter gaps.

## Cause
- `src/domain/agents/product_concepts.py` and `tests/unit/web/test_card686_retired_names_server.py` were written in `CARD-680`/`CARD-686` before `CARD-690`–`CARD-693` consolidated studios and agents.
- `docs/user-guide.md`, `steering/product.md`, `steering/structure.md`, `steering/self-development.md`, and `docs/findings.md` were not updated after `CARD-692` and `CARD-693` landed.
- Full release suite (`preflight.py --release`) is only run before `qa -> main` release and had non-guard unit/integration/Playwright smoke tests still referencing the retired 6-agent roster and retired studio dock buttons.

## Change
- Update `src/domain/agents/product_concepts.py` so `AUTOREIV_CONCEPTS` names the 3 shipped agents (`AutoReiv, Tutor, Direct`) and the **Capabilities** studio (Agora skill folders with `SKILL.md`, `references/`, `tools/*.py`, and `mcp/`).
- Update `docs/user-guide.md`, `steering/product.md`, `steering/structure.md`, and `steering/self-development.md` to match the M26–M28 architecture.
- Prune resolved and obsolete items from `docs/findings.md`, keeping only open, uncarded findings.
- Update `tests/unit/web/test_card686_retired_names_server.py` and add `tests/unit/architecture/test_card694_docs_and_concepts_alignment.py`.
- Fix release-suite issues in `platform/agents/autoreiv.md`, `platform/skills/project-cards/SKILL.md`, `platform/skills/software-development/references/workflow.md`, `src/application/agent_skills/allowed_tools.py`, `src/application/kernel/tool_access.py`, `src/application/observability/journey_canvas.py`, `src/web/static/app.js`, `src/web/static/modules/ui/agent-desktop.js`, `tests/e2e/smoke.spec.js`, and non-guard unit/integration tests.

## What dies
- Stale references to `Architect`, `Developer`, and `Toolsmith` as shipped agents and `Skill Studio` / `Tools Studio` as active studios in `src/domain/agents/product_concepts.py`, `docs/user-guide.md`, `steering/product.md`, `tests/e2e/smoke.spec.js`, and unit/integration suites.
- 31 resolved or obsolete entries in `docs/findings.md`.

## Proof
- Journey `card-694-housekeeping-and-1-1-prep`:
  1. Verify `/api/agents`, `#agentSelect`, and `#view-capabilities` expose the 3-agent roster (`AutoReiv`, `Tutor`, `Direct`) and unified Capabilities studio on desktop and phone.
  2. Ask `AutoReiv` in Chat which agents ship with AutoReiv and which studio manages skills and tools, and verify the reply names `AutoReiv`, `Tutor`, `Direct`, and `Capabilities` without naming retired `Architect`, `Developer`, `Toolsmith`, `Skill Studio`, or `Tools Studio`.
- Checks:
  - `tests/unit/architecture/test_card694_docs_and_concepts_alignment.py` (`pytest.mark.guard`)
  - `tests/unit/web/test_card686_retired_names_server.py`
  - `tests/unit/kernel/test_card680_product_concepts.py`

## Plan and decisions
- **Decision D1 (Housekeeping & v1.1.0 release prep — Approved as Option 1)**: Align `product_concepts.py`, user/steering docs, and `docs/findings.md` with M26–M28 and run release preflight for `v1.1.0`.

## Findings (fixed)
- `platform/agents/autoreiv.md`, `platform/skills/project-cards/SKILL.md`, `platform/skills/software-development/references/workflow.md`: restored `purpose: general` and removed literal `"Ask Developer"` from `autoreiv.md`; added `hand_off_card` to `project-cards/SKILL.md` tools and withheld it from `developer` in `src/application/agent_skills/allowed_tools.py`; added `run_journey` live QA reference to `workflow.md`.
- `src/application/kernel/tool_access.py`: moved `run_project_checks` from `READ_TOOLS` to `WRITE_TOOLS` so custom read-only profiles cannot invoke test suites.
- `src/application/observability/journey_canvas.py`: normalized Windows backslashes and rejected drive-letter absolute paths (`C:\...`) on POSIX in `get_source_snippet`.
- `src/web/static/modules/ui/agent-desktop.js` and `src/web/static/app.js`: added fallback launcher in `launcherForTab(tab)` for views in `VIEW_BY_TAB` without dedicated dock buttons (`skill-studio`, `tools-studio`) and exposed `window.__autoreivSwitchTab`.
- `tests/e2e/smoke.spec.js` and 15 unit/integration test files: updated assertions from retired agents (`developer`, `architect`, `toolsmith`) and retired dock buttons (`#tab-skill-studio`, `#tab-tools-studio`) to the 3-agent roster (`autoreiv`, `tutor`, `direct`) and unified `#tab-capabilities` studio.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-694-housekeeping-and-1-1-prep` | desktop | PASS | 2/2 steps pass; 3-agent roster (`autoreiv`, `direct`, `tutor`), unified Capabilities tree (`capability-authoring`, `project-cards`, `software-development`), and direct concept answer without tool calls or retired names verified |
| `card-694-housekeeping-and-1-1-prep` | phone | PASS | 2/2 steps pass; 3-agent roster, unified Capabilities tree, and direct concept answer verified |

Screenshots:
- `/tmp/autoreiv-qa/card-694/card-694-housekeeping-and-1-1-prep-desktop-01-verify-3-agent-roster-and-unified-capabilities-s.png`
- `/tmp/autoreiv-qa/card-694/card-694-housekeeping-and-1-1-prep-desktop-02-in-chat-autoreiv-answers-a-product-concept-quest.png`
- `/tmp/autoreiv-qa/card-694/card-694-housekeeping-and-1-1-prep-phone-02-in-chat-autoreiv-answers-a-product-concept-quest.png`

## Release note
- Aligned agent product concepts (`AUTOREIV_CONCEPTS`), user and steering documentation, findings backlog, and full release test suite with the 3-agent roster (`AutoReiv`, `Tutor`, `Direct`) and unified Capabilities studio [CARD-694].
