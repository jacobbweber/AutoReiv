# [CARD-150] Chat Session Summaries and Compact Timestamp Badges in History Drawer

> **Status**: In Review
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:feature`, `AutoReiv.Web`, `AutoReiv.Chat`

---

## 1. Why / Intent

In Chat Studio's conversations drawer, past chat sessions are currently hard to differentiate because they all display identical generic names (e.g. "Assistant Chat" or "AutoReiv Chat") with no visible timestamp.

Users need to identify past sessions at a glance. Each session box in the drawer should display:
1. A concise 2–5 word topic summary (e.g. "Postgres Database Setup", "Q3 Budget Review").
2. Directly underneath the summary inside the same compact box, a shorthand date and time badge formatted as `Month DD, Time` (e.g. "Sep 03, 11:50 AM").

---

## 2. What to Build

1. **Frontend Session Card Redesign (`src/web/static/modules/studios/chat.js` & `index.html`)**:
   - In `renderSessionList()`:
     - Change the single-line layout to a stacked, compact two-line box:
       ```text
       +---------------------------------------------+
       | * 2-5 Word Session Summary...               |
       |   Sep 03, 11:50 AM                          |
       +---------------------------------------------+
       ```
     - Add helper `formatSessionTimestamp(isoDateString)` converting UTC ISO timestamps to local `MMM DD, h:mm A` (e.g. "Sep 03, 11:50 AM").
     - Maintain active session highlight styling and mobile touch responsiveness.
2. **Session Title Auto-Summarization (`src/web/routers/chat.py` & `src/infrastructure/memory/repositories/sessions.py`)**:
   - Provide an update mechanism for session titles (`PATCH /api/sessions/{session_id}` or automatic turn-1 summarization).
   - On the first user message turn of a generic session ("New Chat" / "Agent Chat"), generate or extract a clean 2–5 word title from the user prompt and persist it to the `sessions` table.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `[REQ-CHAT-001]`: History drawer session items render a two-line stacked card containing the session title and shorthand timestamp (`Month DD, Time`).
- [x] `[REQ-CHAT-002]`: Generic session titles automatically update to a 2–5 word topic summary based on the initial user turn.
- [x] `[REQ-CHAT-003]`: Timestamps correctly reflect the session's last activity (`updated_at`).
- [x] `[REQ-CHAT-004]`: Compact vertical height preserved to ensure high list density on mobile screens.
- [x] `[REQ-CHAT-005]`: Automated unit tests and frontend tests pass cleanly via `pytest` and `npm test`.
- [x] `[REQ-CHAT-006]`: Zero linting errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags

- Preserves backward compatibility with existing session records in `autoreiv.db`.
- Local `qa` branch is source of truth.
- Follow "How we walk cards with Jacob" rules.
