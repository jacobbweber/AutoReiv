# [CARD-202] Alphabetized Agent Studio Picker

> **Status**: In Review
> **Created**: 2026-09-09
> **Spec Reference**: none
> **Labels**: `type:ui`, `type:refactor`, `in-review`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **No Grouping Headers in Agent Studio Picker**:
   - Remove the `<optgroup>` section headers ("Primary Specialists" and "Internal / Fleet Workers") from the Agent Studio agent dropdown (`#forgeAgentSelect`).
   - Avoid creating an expectation that new agents or systems need to be categorized into specialist vs. internal worker tiers.
2. **Clean Alphabetized List**:
   - Display all available agents in a single, clean, alphabetized list sorted by display name.
3. **Simple Platform vs. Custom Tagging**:
   - The only detail displayed in addition to the agent's display name is `(Platform)` or `(Custom)`.
   - No `[fleet]` prefixes or `(Internal)` badges in the dropdown list.

### Beat 2: What AutoReiv Does Now
- In `src/web/static/modules/studios/forge.js:L731-755`, the agent picker splits agents by `visibility` into two `<optgroup>` containers:
  - "Primary Specialists" for public agents.
  - "Internal / Fleet Workers" for internal specialists, displaying them with fleet tags like `[homelab] (Internal)`.

### Beat 3: What Will Change
1. **Remove Optgroups in Agent Studio**:
   - In `src/web/static/modules/studios/forge.js`, eliminate `optgroup` creation for `#forgeAgentSelect`.
2. **Alphabetical Sorting**:
   - Sort `studioAgents` alphabetically by display name (case-insensitive: `(a.name || a.id).localeCompare(b.name || b.id)`).
3. **Uniform `(Platform)` vs `(Custom)` Labels**:
   - Render each `<option>` as `${a.name} ${a.is_platform_pack || a.is_builtin ? '(Platform)' : '(Custom)'}`.
4. **Automated Unit Verification**:
   - Add a test in `tests/unit/frontend/` verifying the alphabetized sorting, lack of optgroups, and `(Platform)` / `(Custom)` labels.

---

## 2. Acceptance Criteria (Definition of Done)
- [x] **AC-1 (Flat Dropdown)**: Agent Studio dropdown (`#forgeAgentSelect`) contains zero `<optgroup>` elements and renders all agents as direct `<option>` children.
- [x] **AC-2 (Alphabetical Order)**: Agents in `#forgeAgentSelect` are sorted alphabetically by display name from A to Z.
- [x] **AC-3 (Uniform Tags)**: Every option label follows the format `<Name> (Platform)` (if platform pack or built-in) or `<Name> (Custom)`. No `(Internal)` or `[fleet]` tags are displayed.
- [x] **AC-4 (Selection Integrity)**: Retains existing selection on reload or select switch without breaking agent loading or editing.
- [x] **AC-5 (Automated Tests Passing)**: Frontend vitest and backend pytest pass cleanly.

---

## 3. Constraints & Invariants
- Applies to Agent Studio (`#forgeAgentSelect`).
- Chat Studio continues to filter out internal specialist agents (`show_in_chat === false` / `visibility === 'internal'`) so only top-level coordinators and public agents are directly conversational.
- Local `qa` branch workflow.
