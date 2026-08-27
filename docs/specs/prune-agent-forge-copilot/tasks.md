# Task Matrix: Prune Legacy System Architect CoPilot from Agent Forge Studio

## Vertical Slices

### Slice 1: HTML Template Refactor (`[REQ-PRUNE-001, REQ-PRUNE-002]`)
- [ ] Task 1.1: [RED] Review current template structure in `src/web/templates/index.html` under `#view-agents`.
- [ ] Task 1.2: [GREEN] Remove Co-Pilot column and update Character Sheet container to a clean, full-width responsive layout.
- [ ] Task 1.3: [REFACTOR] Ensure responsive styling on mobile and desktop breakpoints.

### Slice 2: JavaScript Module Cleanup (`[REQ-PRUNE-003]`)
- [ ] Task 2.1: [GREEN] Remove Co-Pilot DOM query selectors and event listeners from `src/web/static/modules/studios/forge.js`.
- [ ] Task 2.2: [GREEN] Remove `appendCopilotMessage`, `extractAndOfferBlueprint`, and `checkForBlueprint`.
- [ ] Task 2.3: [REFACTOR] Verify zero null-pointer warnings or errors during Agent Forge initialization.

### Slice 3: Automated Verification & Gate Checks (`[REQ-PRUNE-004]`)
- [ ] Task 3.1: Execute `npm run test:unit:frontend` and `npm run lint:frontend`.
- [ ] Task 3.2: Execute `npm run test:smoke` and `pytest`.
- [ ] Task 3.3: Execute `python .agents/skills/rtm-sync/scripts/preflight.py`.
- [ ] Task 3.4: Synchronize `docs/rtm.json` and `CHANGELOG.md`.
