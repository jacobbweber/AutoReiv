# [CARD-340] Multi-Agent Group Chat and Peer-to-Peer Collaborative Conversation

> **Status**: Ready
> **Created**: 2026-09-16
> **Spec Reference**: docs/specs/multi-agent-group-chat/
> **Labels**: `type:feature`, `domain:chat`, `domain:orchestration`, `domain:multi-agent`

---

## 1. Why / Intent

Currently, Chat Studio is strictly 1-to-1: an operator converses with a single agent at a time. While agents can perform sequential handoffs (`handoff_to_agent`) or execute background jobs, operators cannot assemble a "roundtable" where multiple specialist agents (e.g., `assistant`, `wiki`, `developer`, `tutor`) participate in the same conversation, collaborate in real time, and talk directly to each other.

Jacob wants an agent group chat feature—similar to Grok Bot's multi-agent rooms—where the operator can add multiple agents into an active chat, have a seamless conversation with all of them, and enable the agents to address both the human and each other in a natural, collaborative discussion.

### The Three Beats
1. **What Jacob means**: The operator can invite two or more agents into a single chat session. The user and the agents all share the same chat room. The human can prompt the group or direct questions to specific agents using `@mentions`, and agents can reply to the human or converse with each other to solve a task collaboratively.
2. **What AutoReiv does now**:
   - `ChatSession` stores a single `agent_id`.
   - The Chat Studio header has a single agent selector; switching agents re-binds or re-creates a 1-to-1 session.
   - The execution kernel (`stream_turn` and `run_turn`) expects one agent persona and one set of tool schemas per turn.
   - There is no group turn coordinator, no participant roster, no mention parser, and no peer-to-peer inter-agent conversation loop in chat.
3. **What will change**:
   - **Multi-Agent Session Model**: Extend `ChatSession` with `participants: list[str]` (e.g., `["assistant", "wiki", "developer"]`) and an `active_participants` roster.
   - **Chat Studio Room UI**:
     - Add an "+ Add Agent" participant pill tray in the Chat Studio header (`#chatParticipantTray`).
     - Display distinct visual avatars, agent badges, and colored tone accents for each message bubble so the operator instantly sees who is speaking.
     - Add `@mention` autocomplete in the message composer.
   - **Multi-Agent Turn Coordinator**:
     - Implement `GroupChatCoordinator` in the kernel:
       - **Directed Turns**: If the user (or an agent) says `@wiki ...`, the coordinator dispatches the next turn specifically to `wiki`.
       - **Open Roundtable**: If no agent is explicitly tagged, the primary agent responds or a lightweight router selects the most relevant specialist.
       - **Inter-Agent Dialogue Loops**: When an agent finishes its response, it can hand the microphone to a peer agent or ask a question to another participant.
       - **Runaway Guardrails**: Enforce a strict turn ceiling (e.g., maximum 4 consecutive autonomous agent-to-agent turns before pausing and prompting the operator for input).
   - **Attributed Message History**:
     - Store `sender_agent_id` in `ChatMessage` metadata so the conversation context clearly reflects who spoke (e.g., `[Wiki]: ...`, `[Developer]: ...`), preventing persona confusion.
   - **Harness Synergy**: Pairs directly with CARD-339 (Lean OS Baseline), ensuring that loading multiple agents into a room does not multiply prompt schema bloat.

---

## 2. What to Build

### 1. Data Model & Storage
- Update `ChatSession` model and database schema:
  - Add `participants: list[str]` column / field to `chat_sessions`.
  - Add `sender_agent_id: Optional[str]` to `chat_messages` table and `ChatMessage` domain model.
- Migration in `src/infrastructure/memory/repositories/sessions.py` to support multi-agent sessions seamlessly while maintaining backwards compatibility with 1-to-1 sessions.

### 2. Multi-Agent Turn Coordinator (Backend)
- Implement `GroupChatCoordinator` in `src/application/orchestration/group_chat_coordinator.py`:
  - Mention detection: parses `@<agent_id>` tags in prompts and agent outputs.
  - Turn dispatcher: orchestrates sequential turns for mentioned agents.
  - Autonomous dialogue safety: caps agent-to-agent chained replies to `max_autonomous_turns = 4` to prevent infinite loops and token drain.
  - Expose streaming SSE events: emit `agent_speaking` events with `agent_id` so the UI highlights the currently responding agent.

### 3. Chat Studio Interface (Frontend)
- In `src/web/static/modules/studios/chat.js` and `index.html`:
  - Add `#chatParticipantBar`: displays chips for currently invited agents with a "+" button to invite another installed agent pack.
  - Visual message distinction: render each assistant bubble with the speaking agent's name, avatar icon, and distinct badge styling.
  - Composer mentions: typing `@` in the input triggers a quick-picker popup listing room participants.

---

## 3. Acceptance Criteria (Definition of Done)

- [ ] Operator can create a new group chat or add/remove agents to/from an existing chat session.
- [ ] Chat Studio header displays the active participant roster with clear visual indicators.
- [ ] Message bubbles visually distinguish which agent produced each response (avatar, name, tone badge).
- [ ] `@mention` routing works: typing `@<agent_id>` prompts that specific agent to speak.
- [ ] Inter-agent conversation works: an agent can reference or ask a peer agent, and the peer responds in the same thread.
- [ ] Safety guardrails prevent infinite conversational loops (capped at configurable max autonomous turns before yielding to human).
- [ ] All message history persists accurately with `sender_agent_id` attribution across reloads.
- [ ] Automated backend unit tests (`pytest`) covering `GroupChatCoordinator`, mention parsing, and session persistence.
- [ ] Automated frontend unit tests (`vitest`) covering participant bar, multi-agent message rendering, and mention suggestions.
- [ ] Preflight and linter checks pass with zero errors.

---

## 4. Constraints & Honor Flags

- Zero breaking changes to existing 1-to-1 chat sessions (a 1-to-1 session is simply a group chat with 1 agent participant).
- Respects CARD-339 lean tool baseline: does not mount unnecessary tool schemas for idle participants.
- Dedicated feature branch `feat/CARD-340-multi-agent-group-chat` cut from `qa`.
- No code without Jacob's explicit `build` instruction.
