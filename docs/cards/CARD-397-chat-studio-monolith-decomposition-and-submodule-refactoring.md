---
id: CARD-397
title: "Chat Studio Monolith Decomposition and Submodule Refactoring"
status: In Review
created: 2026-09-21
adr: none
labels:
  - type:refactor
  - area:frontend
  - domain:chat
---

# [CARD-397] Chat Studio Monolith Decomposition and Submodule Refactoring

> **Status**: In Review  
> **Created**: 2026-09-21  
> **ADR Reference**: none  
> **Labels**: `type:refactor`, `area:frontend`, `domain:chat`  

---

## 1. Why / Intent (Beat 1)

`src/web/static/modules/studios/chat.js` stands at **4,118 lines**, far exceeding the 800-line monolith limit defined in `.agents/rules/code-hygiene-and-pruning.md` Section 5.
Large monolithic studio files create context-window blindness, increase cognitive load, and breed duplicate event listeners and shadow functions.
Decomposing `chat.js` into focused, single-responsibility submodules makes the chat engine clean, testable, and maintainable without altering any external behavior.

---

## 2. What AutoReiv Does Now (Beat 2)

- Although early extraction created `chat/hitl.js`, `chat/training.js`, `chat/scroll.js`, and `chat/stream.js`, the main `chat.js` file still houses over 3,200 lines of mixed concerns:
  - Message rendering (thought bubbles, deliverable markdown, tool invocation cards, code copy blocks).
  - Composer input management (auto-resize textarea, file attachments, drag-and-drop, keybindings).
  - Session drawer & navigation chrome (session listing, switching, renaming, deleting, search filtering).
  - Runbook / quick prompt drawers and options menus.

---

## 3. What Will Change (Beat 3)

- Decompose `src/web/static/modules/studios/chat.js` into dedicated submodules under `src/web/static/modules/studios/chat/`:
  - `src/web/static/modules/studios/chat/render.js`: Message DOM builders, thinking toggle blocks, tool call cards, markdown deliverable formatters, and code block copy buttons.
  - `src/web/static/modules/studios/chat/composer.js`: Textarea input listeners, attachment management, media paste/drop handling, and send/stop control levers.
  - `src/web/static/modules/studios/chat/chrome.js`: Sessions drawer, session persistence, title renaming, agent selector sync, and quick prompts drawer.
- Refactor `src/web/static/modules/studios/chat.js` to serve as a cohesive controller (<800 lines) that coordinates the submodules, exposes `initChatStudio(state, callbacks)`, and re-exports public symbols for backward compatibility.
- Ensure all 102 frontend test suites and Playwright E2E suites pass with zero regressions.

---

## 4. What Dies Today (The Prune List - Beat 4)

- **Monolithic Inlining**:
  - Over 3,200 lines of tightly coupled monolithic functions in `src/web/static/modules/studios/chat.js` retired in favor of pure, focused submodule exports.
- **Shadow Event Listeners**:
  - Any duplicate DOM bindings or redundant helpers discovered during extraction.

---

## 5. Acceptance Criteria (EARS Syntax)

- **Ubiquitous**: THE SYSTEM SHALL keep all JavaScript files in `src/web/static/modules/studios/` under the 800-line limit (or well below 1,000 lines for the root orchestrator).
- **Ubiquitous**: THE SYSTEM SHALL maintain full backward compatibility for all exports from `src/web/static/modules/studios/chat.js`.
- **Event-Driven**: WHEN a user sends a message, uploads an attachment, or switches sessions, THE CHAT STUDIO SHALL behave identically to the baseline.
- **Negative Assertion**: Automated tests shall assert that `src/web/static/modules/studios/chat.js` is under 1,000 lines of code.
- **Negative Assertion**: Automated tests shall verify that all 608 Vitest frontend tests continue to pass without modification to business logic.

---

## 6. Constraints & Verification Plan

- Standard honor constraints apply.
- Zero functional regressions in Chat Studio.
- Feature branch cut from `qa`: `feat/card-397-chat-monolith-decomposition`.
- Verification via `npm run test:unit:frontend`, `npm run lint:frontend`, and Playwright chat smoke tests.
