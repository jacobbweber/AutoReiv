# [CARD-157] Host Command Auto-Delegation, Nested HITL Approval Flow, and Chat Bubble Lifecycle

> **Status**: Done
> **Created**: 2026-09-04
> **Spec Reference**: none
> **Labels**: `type:bugfix`, `AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Chat`

---

## 1. Why / Intent

During chat sessions where users interact with Assistant to run host diagnostics or terminal commands (e.g. `ipconfig`, network checks), three interconnected defects broke the expected user experience:

1. **Assistant Declining Host Commands**: Assistant's system prompt lacked an explicit directive for host CLI execution. Instead of delegating to AutoReiv via `handoff_to_agent`, Assistant hallucinated a sandboxed `execute_code` limitation and told the user to run the command manually.
2. **Missing Subagent Approvals & Premature Parent Resume**: When delegated to AutoReiv, multi-step approvals (e.g. OS detection followed by `ipconfig /all`) caused the parent Assistant to prematurely wake up and speak because `shouldResumeChatAfterHitl` resumed the parent turn while the subagent was still waiting on an intermediate approval. Furthermore, `/api/approvals/pending` filtered by `agent_id=assistant`, hiding AutoReiv's approval cards in the UI.
3. **Erased User Prompt & Stuck "Streaming..." Badge**: In `executeChatTurn()`, `loadMessages(state.activeSessionId, { force: true })` was called before setting `isStreaming = true`. This wiped the user prompt bubble that had just been appended to the DOM, replaced it with the "Start a new conversation..." empty state placeholder, and left the `Streaming...` badge stuck in the top-right corner indefinitely.

---

## 2. What to Build

1. **Host Command Delegation Prompting (`platform-packs/assistant/pack.json` & `src/domain/agents/profiles.py`)**:
   - Update Assistant's prompt to explicitly instruct:
     *"You do not have direct host shell access. Whenever the user requests running host terminal, CLI, PowerShell, bash, or network/hardware commands (such as ipconfig, ping, disk checks, process listing, or system configuration), you MUST immediately delegate the execution to the 'autoreiv' platform agent via `handoff_to_agent` (target_agent='autoreiv') and report back the results."*

2. **Subagent-Aware Pending Approvals (`src/infrastructure/memory/repositories/approvals.py` & `src/web/routers/hitl.py`)**:
   - Update `get_pending_approvals(session_id=...)` to match both the exact session ID and all child/phase sessions (`session_id = ? OR session_id LIKE ? || '_child_%' OR session_id LIKE ? || '::phase::%'`).
   - In `src/web/static/modules/studios/chat.js` (`refreshPendingHitl`), query pending approvals for the active session (and its children) without restricting to the parent `agent_id`.

3. **Chained Subagent HITL Flow (`src/web/static/modules/studios/chat.js`)**:
   - In `submitHitlDecision()` and `shouldResumeChatAfterHitl()`:
     - Check if the resolved approval response contains `nested.status === 'approval_required'`.
     - If a nested child is still waiting on another approval, do NOT resume the parent chat turn. Immediately render the new pending approval card in the UI.

4. **User Prompt Preservation & Streaming Badge Cleanup (`src/web/static/modules/studios/chat.js`)**:
   - In `executeChatTurn()`:
     - Remove the premature `loadMessages()` call at turn initiation.
     - Immediately set `state.isStreaming = true` upon form submission.
     - Clean up any empty conversation placeholder (`"Start a new conversation with..."`) from `messagesContainer` when appending user bubbles.
     - In the turn completion handler and abort handler, explicitly remove/hide the `Streaming...` pulse indicator from `streamBubble`.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `[REQ-CHAT-015]`: When asked to run host shell/terminal commands, Assistant automatically delegates to AutoReiv via `handoff_to_agent`.
- [x] `[REQ-CHAT-016]`: User prompt bubble remains visible in the chat DOM when sent, and the empty session placeholder is removed.
- [x] `[REQ-CHAT-017]`: The "Streaming..." pulse badge is cleaned up and hidden when generation finishes or pauses for HITL approval.
- [x] `[REQ-CHAT-018]`: Multi-step subagent approvals correctly surface their HITL cards in the chat view without being filtered out by agent ID.
- [x] `[REQ-CHAT-019]`: Subagent approvals chained across multiple steps do not trigger premature parent assistant turns while intermediate approvals are pending.
- [x] `[REQ-CHAT-020]`: Automated unit tests and frontend tests pass cleanly via `pytest` and `npm run test:unit:frontend`.
- [x] `[REQ-CHAT-021]`: Zero linting errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags

- Zero regressions to routine execution approvals or single-agent HITL flows.
- Local `qa` branch is source of truth.
- Follow "How we walk cards with Jacob" rules: card stays Ready until Jacob says build.
