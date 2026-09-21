---
id: CARD-398
title: "Agent Forge Studio Monolith Decomposition and Submodule Refactoring"
status: Done
created: 2026-09-21
adr: none
labels:
  - type:refactor
  - area:frontend
  - domain:forge
---

# [CARD-398] Agent Forge Studio Monolith Decomposition and Submodule Refactoring

> **Status**: Done  
> **Created**: 2026-09-21  
> **ADR Reference**: none  
> **Labels**: `type:refactor`, `area:frontend`, `domain:forge`  

---

## 1. Why / Intent (Beat 1)

`src/web/static/modules/studios/forge.js` stands at **3,505 lines**, dramatically exceeding the 800-line monolith threshold established in `.agents/rules/code-hygiene-and-pruning.md` Section 5.
Large monolithic files induce context-window blindness, increase cognitive load, and breed duplicate handlers and shadow functions.
Decomposing `forge.js` into focused, single-responsibility submodules under `src/web/static/modules/studios/forge/` makes Agent Forge maintainable, testable, and robust without altering any external user-facing behaviors or breaking existing public APIs.

---

## 2. What AutoReiv Does Now (Beat 2)

`src/web/static/modules/studios/forge.js` houses all of the following heterogeneous concerns in a single monolithic 3,505-line file:
- Runbook authoring, markdown editing, character counting, and mechanical capability linting.
- Platform skill loading, pack skill tree rendering, nested home accordions, and declared tool chips.
- Baseline tool cards, MCP server configuration, credential grants, and capability gap analysis.
- Autonomous factory lab monitor drawer, job packet telemetry, and artifact preview modals.
- Quick scaffold modal, quick presets, scaffold approval queue, and origin resumption.
- Architectural proposals inspection, status badges, and proposal synthesis.
- Model discovery, provider dropdowns, context window handling, tone management modal, and brain drawer telemetry.

---

## 3. What Will Change (Beat 3)

Decompose `src/web/static/modules/studios/forge.js` into focused submodules under `src/web/static/modules/studios/forge/`:
1. `src/web/static/modules/studios/forge/runbook.js` (<800 lines):
   Runbook editor DOM management (`openRunbookEditor`, `hideRunbookEditor`, `applyRunbook`), character counter, mechanical capability linting (`validateActiveRunbook`, `renderRunbookLintReport`), platform and pack skill row rendering (`renderPlatformSkills`, `renderPackSkills`, `bindSkillRowHandlers`).
2. `src/web/static/modules/studios/forge/tools.js` (<800 lines):
   Baseline tool cards (`renderBaselineTools`, `renderToolBadgeHtml`), MCP server configurations (`loadAgentMcpServers`, `renderAgentMcpServers`), credential grants (`loadAgentCredentialGrants`), and capability gaps (`loadAgentCapabilityGaps`).
3. `src/web/static/modules/studios/forge/lab_monitor.js` (<800 lines):
   Training factory lab monitor drawer (`openLabMonitorDrawer`, `closeLabMonitorDrawer`), packet feed formatters, packet artifact extraction, job status indicators, and artifact preview modal.
4. `src/web/static/modules/studios/forge/scaffold.js` (<800 lines):
   Quick presets (`FORGE_QUICK_PRESETS`), quick scaffold modal (`openQuickScaffoldModal`, `closeQuickScaffoldModal`, `buildQuickScaffoldPayload`), scaffold queue, and origin resumption.
5. `src/web/static/modules/studios/forge/proposals.js` (<800 lines):
   Architectural proposal badges (`renderProposalBadgeHtml`), proposal cards (`renderProposalCardHtml`), proposal loading, and synthesis actions.
6. `src/web/static/modules/studios/forge/config.js` (<800 lines):
   Model provider dropdowns and discovery (`populateAgentModelSelect`, `discoverModelsForAgent`), tone manager modal (`openManageTonesModal`, `renderManageTonesList`), brain drawer (`loadAndRenderBrainDrawer`), telemetry, and assigned routines.
7. `src/web/static/modules/studios/forge.js` (<1,000 lines):
   Root coordinator managing studio initialization (`initAgentForge`), agent selection and forms (`loadAgentForge`, `renderAgentToForge`), save and delete actions, and re-exporting all submodule symbols for complete backward compatibility.

---

## 4. What Dies Today (The Prune List - Beat 4)

- **Monolithic Inlining**:
  - Over 2,500 lines of tightly coupled monolithic functions in `forge.js` retired in favor of cohesive submodule exports.
- **Redundant State Trackers**:
  - Any duplicate state variables or ad-hoc DOM queries eliminated across submodules.

---

## 5. Acceptance Criteria (EARS Syntax)

- **Ubiquitous**: THE SYSTEM SHALL keep all JavaScript files in `src/web/static/modules/studios/forge/*.js` under 800 lines of code.
- **Ubiquitous**: THE SYSTEM SHALL keep `src/web/static/modules/studios/forge.js` under 1,000 lines of code.
- **Ubiquitous**: THE SYSTEM SHALL maintain complete backward compatibility for all exports from `src/web/static/modules/studios/forge.js`.
- **Event-Driven**: WHEN a user edits a runbook, selects tools, modifies agent settings, or views the lab monitor, THE AGENT FORGE STUDIO SHALL behave identically to the baseline.
- **Negative Assertion**: Automated tests shall explicitly assert that `forge.js` line count is strictly less than 1,000 lines.
- **Negative Assertion**: Automated tests shall assert that all submodules under `src/web/static/modules/studios/forge/` are strictly less than 800 lines.
- **Negative Assertion**: Automated tests shall verify that all existing frontend Vitest and Playwright smoke tests pass with zero regressions.

---

## 6. Constraints & Verification Plan

- Standard honor constraints apply.
- Zero breaking changes to existing tests.
- Feature branch cut from `qa`: `feat/card-398-forge-monolith-decomposition`.
- Verification via `npm run test:unit:frontend`, `npm run lint:frontend`, and `npm run test:smoke`.
