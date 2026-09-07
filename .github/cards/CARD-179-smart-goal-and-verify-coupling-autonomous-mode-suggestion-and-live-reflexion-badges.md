# [CARD-179] Smart Goal and Verify Coupling, Autonomous Mode Suggestion, and Live Reflexion Badges

> **Status**: In Review
> **Created**: 2026-09-07
> **Spec Reference**: docs/specs/orchestration/; docs/specs/kernel/
> **Labels**: `type:feature`, `type:ui`, `AutoReiv.Chat`, `AutoReiv.Kernel`, `AutoReiv.Orchestration`

---

## 1. Why / Intent

Align AutoReiv's chat execution modes with industry best practices:
- When a user initiates **Plan & Execute (Goal Mode)**, the system should automatically pair it with **Reflexion (Verify)** by default, because multi-step projects depend on each step passing validation.
- When a user enters a complex multi-step prompt in normal chat, the agent should autonomously offer to switch to **Goal & Verify Mode** with a single click.
- When verification is active, the chat stream should visually surface the critic's inspection and any auto-retry attempts so the user can see self-correction happening in real-time.

---

## 2. Three Beats: How It Works

### Beat 1: Smart Checkbox Coupling
1. **What you see**: In the Chat bar, clicking the **Goal** checkbox automatically turns ON the **Verify** checkbox. (You can still manually uncheck Verify if you want maximum speed and fewer tokens).
2. **What AutoReiv does now**: Goal and Verify are two independent checkboxes in `src/web/static/modules/studios/chat.js` with no automatic coupling.
3. **What will change**: Checking Goal sets Verify to true automatically.

### Beat 2: Live Reflexion Badges in Chat
1. **What you see**: While a phase or turn runs with Verify enabled, a small badge appears in the chat bubble:
   - `[🔍 Verifying output...]`
   - `[↺ Attempt 1 had discrepancies -> Auto-correcting...]`
   - `[✓ Verified against success rule]`
   Clicking the badge expands to show what the critic checked.
2. **What AutoReiv does now**: The critic in `src/application/kernel/reflexion_engine.py` runs quietly in Python. The UI only receives the final answer, keeping the self-correction invisible.
3. **What will change**: `chat.py` will emit SSE events (`verify_status`) containing the critic payload, and `chat.js` will render the live badge.

### Beat 3: Autonomous Mode Suggestion
1. **What you see**: If you type a complex project prompt into normal chat without Goal mode selected, the agent detects the multi-step nature and presents a quick action button: `[Switch to Goal & Verify Mode]`.
2. **What AutoReiv does now**: Normal chat runs a single-turn ReAct loop regardless of how big the prompt is, unless you manually remembered to tick Goal Mode beforehand.
3. **What will change**: A lightweight intent check offers a 1-click upgrade to Goal+Verify.

---

## 3. Technical Touchpoints

| Layer | Component | File Path |
| :--- | :--- | :--- |
| **Frontend UI** | Chat Studio Checkbox Coupling & Badges | `src/web/static/modules/studios/chat.js` |
| **Streaming Gateway** | Chat SSE Event Streaming | `src/web/routers/chat.py` |
| **Reflexion Engine** | Critic payload streaming hook | `src/application/kernel/reflexion_engine.py` |

---

## 4. Acceptance Criteria (Definition of Done)

- [x] [REQ-REF-001] Checking the **Goal** checkbox in Chat automatically checks **Verify** unless the user explicitly unticks it.
- [x] [REQ-REF-002] The backend Reflexion loop emits SSE events (`verify_status` / `reflexion_attempt`, `reflexion_critique`, `reflexion_verified`) indicating evaluation start, critique discrepancies, and passing status.
- [x] [REQ-REF-003] The Chat UI renders a collapsible verification badge under the active message showing live critic progress.
- [x] [REQ-REF-004] An autonomous prompt heuristic in Chat suggests switching to Goal + Verify mode when a complex multi-action prompt is received in default chat.
- [x] [REQ-REF-005] All automated unit and integration tests pass cleanly via `pytest` and `vitest`.
- [x] [REQ-REF-006] Zero lint errors via `ruff check .`.

---

## 5. Constraints & Working Agreement

- **Ready card only. Do not implement until Jacob explicitly says build.**
- Work strictly on local `qa` branch.
- No third-party product names in card or code.
