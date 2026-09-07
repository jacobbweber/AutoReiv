# [CARD-187] Human-Readable HITL Approval Previews and Routines Management Fixes

> **Status**: In Review
> **Created**: 2026-09-07
> **Spec Reference**: docs/specs/orchestration/; docs/specs/hitl/
> **Labels**: `type:bugfix`, `type:ui`, `AutoReiv.Chat`, `AutoReiv.Routines`, `AutoReiv.Web`

---

## 1. Why / Intent

1. **Human-In-The-Loop (HITL) Readability**: When an agent requests operator approval to run code or shell commands (e.g. `execute_code`, `cli_exec`, `write_file`), the operator needs to review what code will actually execute before approving it. Currently, passing the arguments and execution results through raw `JSON.stringify` turns all newlines into escaped text `\n` and quotes into `\"`, making code blocks and terminal outputs hard to read.
2. **Routines Management Reliability**: Clicking "Delete" on routines in the Routines Studio either does nothing or silently fails on mobile devices because built-in routines display Delete buttons by mistake, error feedback is placed in a banner hidden off-screen, and mobile browsers can suppress blocking `confirm()` dialogs.

---

## 2. Three Beats: How It Works

### Beat 1: Human-Readable HITL Code & Command Preview (Tool Input)
1. **What you see**: In the Chat view inside the yellow/amber "Approval required" card, the code or shell command is rendered directly as clean, formatted multiline text (real newlines and indentation, no escaped `\n` or surrounding JSON quotes). If there are other arguments (e.g. `timeout` or `path`), they are cleanly labeled above the code block.
2. **What AutoReiv does now**: In [`src/web/static/modules/studios/chat.js`](src/web/static/modules/studios/chat.js) (`formatHitlArgs`), the whole argument dictionary is dumped into `JSON.stringify(args, null, 2)`. This turns multi-line code strings into escaped JSON string properties with literal `\n`.
3. **What will change**: `formatHitlArgs` will detect primary script/command payloads (`code`, `command`, `script`, `sql`, `query`, or `prompt`). It renders the actual code unescaped and formatted, with accompanying metadata displayed cleanly.

### Beat 2: Direct Standard Output Display (Tool Output)
1. **What you see**: When the tool completes execution, the output box renders the actual standard output (`stdout`) directly as clean terminal output or formatted JSON, without wrapping it in an outer execution JSON envelope full of escaped `\r\n`.
2. **What AutoReiv does now**: In [`src/web/static/modules/studios/chat.js`](src/web/static/modules/studios/chat.js) (`submitHitlDecision`), the card appends `JSON.stringify(output, null, 2)`. Because `output` is `{ success: true, stdout: "..." }`, any string inside `stdout` is escaped with `\r\n` and `\"`.
3. **What will change**: When rendering execution results, if `output.stdout` or `output.stderr` is present, it extracts and displays the clean string directly. If `stdout` itself contains valid JSON, it pretty-prints it cleanly.

### Beat 3: Reliable Routine Deletion & Built-in Protection
1. **What you see**: In the Routines Studio (`/routines`), built-in platform routines (like `daily-sysinfo`, `nightly-hygiene`, `hourly-sre-pulse`, `morning-briefing`, etc.) never show a Delete button. User-created routines show a Delete button with reliable confirmation, and deletion immediately removes the card and shows a floating toast notification.
2. **What AutoReiv does now**: In [`src/web/routers/routines.py`](src/web/routers/routines.py), `list_routines` does not return `is_builtin`. The frontend in [`routines.js`](src/web/static/modules/studios/routines.js) uses an incomplete hardcoded list of built-in routine names, displaying Delete buttons on built-in routines. Clicking delete sends a request that the backend rejects (`400`), and the error is printed to an off-screen status banner without a toast notification.
3. **What will change**:
   - `GET /api/routines` returns `is_builtin: boolean` matching `BUILTIN_ROUTINES`.
   - The frontend hides Delete on any routine where `is_builtin` is true.
   - Deleting a user routine uses reliable confirmation, executes `DELETE /api/routines/{id}`, refreshes the grid, and displays completion via `showToast`.

---

## 3. Technical Touchpoints

| Layer | Component | File Path |
| :--- | :--- | :--- |
| **Frontend UI** | Chat Studio HITL Card Rendering | `src/web/static/modules/studios/chat.js` |
| **Frontend UI** | Routines Studio Card Actions | `src/web/static/modules/studios/routines.js` |
| **Backend API** | Routines Router | `src/web/routers/routines.py` |
| **Tests** | Frontend Unit Tests | `tests/unit/frontend/chat_modes.test.js` |
| **Tests** | Routines API Unit Tests | `tests/unit/web/test_routine_management_api.py` |

---

## 4. Acceptance Criteria (Definition of Done)

- [x] [REQ-HITL-050] `formatHitlArgs` in `chat.js` formats code and command tool arguments as clean, unescaped multiline text instead of JSON-escaped strings with literal `\n`.
- [x] [REQ-HITL-051] `submitHitlDecision` in `chat.js` renders tool execution output by extracting `stdout` / `stderr` directly rather than JSON-stringifying the outer execution envelope with `\r\n`.
- [x] [REQ-ROUTINE-050] `GET /api/routines` includes `is_builtin` boolean on each routine item matching `BUILTIN_ROUTINES`.
- [x] [REQ-ROUTINE-051] Routines Studio UI hides the Delete button for all built-in routines (`is_builtin === true`).
- [x] [REQ-ROUTINE-052] Deleting a user routine provides reliable confirmation, executes `DELETE /api/routines/{id}`, refreshes the grid, and displays a toast notification via `showToast`.
- [x] [REQ-TEST-050] All automated frontend (`vitest`) and backend (`pytest`) tests pass cleanly.
- [x] [REQ-LINT-050] Zero lint errors via `ruff check .`.

---

## 5. Constraints & Working Agreement

- **Ready card only. Do not implement until Jacob explicitly says build.**
- Work strictly on local `qa` branch. Local commits only. No push, no tag, no merge to `main`.
- No third-party product names in card or code.
