# [CARD-140] Remove Obsolete Wiki Knowledge Graph Modal and Button

> **Status**: In Review
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:chore`, `needs-triage`

---

## 1. Why / Intent
The Wiki Knowledge Graph Modal (`#wikiGraphModal`) and its toolbar trigger button (`#wikiGraphViewBtn`) rendered a static/unusable Mermaid diagram that provided no real value on desktop or mobile. The interactive Force-Directed Mind Map (`#wikiMindMapModal`) already provides superior Obsidian-style graph visualization. Removing this redundant feature simplifies the Wiki Studio toolbar and eliminates dead code.

---

## 2. What to Build
1. **Remove Toolbar Trigger**:
   - Delete `#wikiGraphViewBtn` from the Wiki Studio top bar in `src/web/templates/index.html`.
2. **Remove Modal Markup**:
   - Delete `#wikiGraphModal` and its children (`#wikiGraphModalTitle`, `#wikiGraphCloseBtn`, `#wikiGraphContainer`) from `src/web/templates/index.html`.
3. **Clean Up JavaScript Handlers**:
   - Remove references and event listeners for `wikiGraphViewBtn`, `wikiGraphModal`, `wikiGraphCloseBtn`, and `wikiGraphContainer` from `src/web/static/modules/studios/wiki.js`.
   - Remove `wikiGraphModal` and `#wikiGraphCloseBtn` from modal management in `src/web/static/app.js`.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-CLEAN-001]` `#wikiGraphViewBtn` is removed from `index.html`.
- [ ] `[REQ-CLEAN-002]` `#wikiGraphModal` is removed from `index.html`.
- [ ] `[REQ-CLEAN-003]` JavaScript controllers in `wiki.js` and `app.js` are cleaned of all graph modal references without warnings.
- [ ] Automated tests green via `npm run test:unit:frontend` and `pytest tests/unit/web`.
- [ ] Zero lint errors via `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags
- Preserve the interactive Mind Map (`#wikiMindMapViewBtn` / `#wikiMindMapModal`).
- Zero regressions in existing frontend and backend tests.
