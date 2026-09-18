# [CARD-358] Persistent Skill Proposal Cards in Chat History

> **Status**: Done  
> **Created**: 2026-09-18  
> **Spec Reference**: `docs/specs/in-situ-skill-distillation/`, `docs/cards/CARD-352-in-situ-skill-workshop-learn-distillation-from-chat.md`  
> **Labels**: `type:bug`, `type:enhancement`, `AutoReiv.Web`, `AutoReiv.Chat`, `domain:skills`, `domain:ux`  

---

## 1. Three Beats

### Beat 1: What Jacob means
When an operator clicks `[ 💡 Teach Agent ]` on an assistant message in Chat Studio and submits guidance, the distillation engine synthesizes a **Skill Proposal Card**. Currently, this card is inserted into the chat as an ephemeral, unpersisted DOM node. If the operator clicks anywhere in the chat window, opens the accordion preview, switches focus to another app, or refreshes the page, the entire proposal card vanishes instantly because `loadMessages` and `renderMessages` clear the message container and only re-render stored database messages. The operator loses the proposal and must click `Teach Agent` all over again.

Jacob wants the Skill Proposal Card to be a **first-class, persistent artifact of the chat history**—just like tool call cards and user/assistant messages. It must stay in the chat transcript permanently across clicks, window refocusing, tab switching, and page reloads. When the operator makes a decision (e.g. clicking `[ ✅ Adopt Skill ]` or `[ 🚀 Send to Factory ]`), the card should remain in the chat stream with an immutable receipt of the adoption.

### Beat 2: What AutoReiv does now
1. **No Backend Persistence**: `POST /api/skills/distill` generates a proposal dictionary and returns it as a transient JSON payload. Nothing is saved to the SQLite `messages` or `session_artifacts` table for that session.
2. **Brittle Frontend DOM Injection**: `renderSkillProposalCard(proposal)` in `chat.js` merely appends `el` to `messagesContainer`.
3. **Wiped by Window Refocus & Background Polls**:
   - In `chat.js`, `window.addEventListener('focus')` and `document.addEventListener('visibilitychange')` call `loadMessages(state.activeSessionId)`.
   - `loadMessages()` only protects `.hitl-approval-card` (`hasVisibleHitlCard`). It has no protection for `.skill-proposal-card`.
   - `loadMessages()` calls `renderMessages()`, which executes `messagesContainer.innerHTML = ''` and re-renders only messages fetched from the database.
   - Any background polling or session re-query instantly destroys the proposal card.
4. **Transient Adoption State**: Even if the operator manages to click `Adopt Skill` before refocusing, the button state mutation is only in local DOM memory. On next refresh or message sent, the record of the learned skill is erased from the conversation view.

### Beat 3: What will change
1. **Backend Proposal Persistence (`distillation_service.py`, `skills.py`)**:
   - When `/api/skills/distill` completes, the distilled proposal is saved into the session's chat transcript as a message with `role: "skill_proposal"` (storing proposal metadata, plain summary, and runbook markdown in `content` / `tool_calls_json`).
   - When `/api/skills/adopt` is called, the message payload is updated to record adoption status (`status: "adopted"` and timestamp).
2. **Chat Stream Renderer (`chat.js`)**:
   - `renderMessageItem(msg)` natively recognizes `role === 'skill_proposal'`.
   - Reconstructed from the database on every page load, session switch, and refocus, rendering the interactive `.skill-proposal-card`.
   - If the proposal was already adopted, it renders in the completed/adopted state (`Skill mounted to <agent>`).
3. **DOM Safety in `loadMessages`**:
   - `hasVisibleHitlCard` or an expanded `hasActiveInteractiveCard` check ensures transient in-flight states are never wiped mid-interaction.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] `POST /api/skills/distill` persists the synthesized proposal into the conversation session as a persistent message (`role: "skill_proposal"`).
- [x] Clicking into the chat, focusing another window, or switching browser tabs does not remove or hide the Skill Proposal Card.
- [x] Refreshing the browser or reloading the session keeps the Skill Proposal Card visible in its exact position in the conversation history.
- [x] Clicking `[ ✅ Adopt Skill ]` records the adoption in the database, so reloading the session retains the "Skill mounted to <Agent>" badge permanently.
- [x] If a proposal requires Factory Studio escalation, that state is also preserved across reloads.
- [x] Automated tests cover distillation message persistence, session reload rendering, and adoption status updates.
- [x] Zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 3. Constraints & Honor Flags
- Skills must continue to be saved strictly under user data packs (`packs/<agent_id>/skills/`), never under git checkout.
- No code without Jacob's explicit `build` instruction.
