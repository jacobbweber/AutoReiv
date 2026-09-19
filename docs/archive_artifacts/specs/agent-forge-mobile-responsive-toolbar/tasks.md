# Task Matrix: Agent Forge Studio Mobile Responsive Toolbar and UI Polish

## Vertical Slices

### Slice 1: Header Badge Removal & Responsive Toolbar Layout (`[REQ-MOB-001, REQ-MOB-002]`)
- [ ] Task 1.1: [GREEN] Remove `RPG Character Sheet` badge in `src/web/templates/index.html`.
- [ ] Task 1.2: [GREEN] Refactor Agent Forge top toolbar to mobile-first responsive wrapping flexbox layout.
- [ ] Task 1.3: [REFACTOR] Verify button alignment and tap targets on narrow viewports ($\le 380\text{px}$).

### Slice 2: Default Collapsed Skill Packs (`[REQ-MOB-003]`)
- [ ] Task 2.1: [GREEN] Update `renderSkillsCatalog` in `src/web/static/modules/studios/forge.js` to render `.pack-tools-grid` with `hidden` class by default.
- [ ] Task 2.2: [GREEN] Set initial chevron rotation to `-90deg` and verify smooth expand/collapse on click.

### Slice 3: Verification & Gate Checks (`[REQ-MOB-004]`)
- [ ] Task 3.1: Execute `npm run test:unit:frontend` and `npm run lint:frontend`.
- [ ] Task 3.2: Execute `npm run test:smoke` and `pytest`.
- [ ] Task 3.3: Execute `python .agents/skills/rtm-sync/scripts/preflight.py`.
- [ ] Task 3.4: Synchronize `docs/rtm.json` and `CHANGELOG.md`.
