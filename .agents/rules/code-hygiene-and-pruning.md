---
trigger: always_on
description: Code hygiene, dead-code elimination, Single Lever invariant, Beat 4 (the prune list), and monolith decomposition.
---

# Rule: Code Hygiene, Anti-Duplication, and Pruning Protocol

## 1. Philosophy: Subtractive Engineering

Codebases rot not from what is added, but from what fails to be deleted. When requirements or architectures shift, AI coding assistants naturally suffer from **Additive Bias ("Patch-on-Top" Syndrome)**: wrapping new logic around obsolete code rather than excising it.

Every feature, bug fix, and refactor MUST be subtractive as well as additive. If an old path is superseded, it must be deleted immediately.

---

## 2. The Four Beats (Mandatory Beat 4: What Dies Today)

Before modifying or generating code, the agent must present the **Four Beats** to Jacob:

1. **What Jacob means**: The core product intent and user experience goal.
2. **What AutoReiv does now**: The current code path, DOM structure, and behavior.
3. **What will change**: The technical modifications and new primitives to be introduced.
4. **What dies today (The Prune List)**: The explicit, non-empty list of every function, variable, class, DOM element, CSS rule, API route, or legacy flag being **retired, deleted, or superseded**.

> If a card changes direction or replaces a behavior, the agent cannot proceed until the Prune List is declared and executed.

---

## 3. The Single Lever Invariant (Zero Duplicate Paths)

Every user capability, UI interaction, event handler, or state transition MUST have **exactly ONE code path**.

- **No Shadow Functions**: If a function already renders messages, manages job chrome, or parses streams, do NOT create a second function or helper doing similar work. You must modify the canonical function or completely replace and delete the old one.
- **No Duplicate Levers**: Never maintain two UI controls, two event listeners, or two API endpoints for the same operator job. Two levers for one job is an immediate architectural defect.
- **Single Source of State**: Shared state belongs in the canonical store, never duplicated across parallel variables or ad-hoc DOM attributes.

---

## 4. The Scavenger Pass (Mandatory Callers & Dead-Code Audit)

Before declaring any card `In Review` or `Done`, the agent MUST execute a Scavenger Pass:

1. **Callers Audit**:
   - Run a ripgrep search (`grep_search`) across the entire repository for every function, symbol, or constant that was touched or superseded.
   - Verify that ZERO orphaned callers, obsolete imports, or dead references remain.
2. **Dead Code & Zombie Element Elimination**:
   - Delete obsolete functions, unreachable `if/else` branches, and commented-out legacy code.
   - Remove unused CSS classes, orphaned HTML element IDs, and deprecated test fixtures.
3. **Static Linter Zero-Tolerance**:
   - `ruff check .` must pass with 0 errors (catching unused imports and unused variables).
   - `npm run lint:frontend` must pass with 0 errors and 0 warnings.

---

## 5. Monolith Decomposition Guidelines (File Size Caps)

Files that exceed **800 lines** (such as legacy monolithic studios) cause context-window blindness in LLMs, directly breeding duplicate functions and unintended side effects.

- When tasked with refactoring or fixing bugs in a monolithic file (>800 lines), the agent should identify opportunities to decompose the file into focused, single-responsibility submodules (e.g. splitting `chat.js` into `chat_stream.js`, `chat_dom.js`, `chat_chrome.js`).
- Keep submodules cohesive, export clean interfaces, and maintain clear import graphs.
