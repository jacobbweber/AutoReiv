---
id: CARD-434
title: "Education Studio Monolith Decomposition and Submodule Refactoring"
status: Superseded
created: 2026-09-23
adr: none
labels:
  - type:refactor
  - area:frontend
  - domain:education
  - P0
---

# [CARD-434] Education Studio Monolith Decomposition and Submodule Refactoring

> **Status**: Superseded
> **Created**: 2026-09-23
> **Baseline**: `qa` / `main` @ `881cb276` (v0.42.0)
> **Prior attempt**: local `feat/card-400-education-monolith-decomposition` @ `ed1f6a6f` (not merged; 146 commits behind tip)
> **ADR Reference**: none
> **Labels**: `type:refactor`, `area:frontend`, `domain:education`, `P0`
> **Superseded by**: [CARD-435](./CARD-435-education-tutor-first-direction.md) (Education Tutor-first direction)
> **Supersession note** (2026-09-23): Do **not** implement this card. Tutor in education mode (Learning OS rails + Wiki library) is the Study/coaching entry. Education Studio **stays** as flashcard/quiz/test **player** ([ADR-0059](../adr/0059-education-studio-as-quiz-flashcard-and-test-player.md), [CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md)); retirement [CARD-442](./CARD-442-retire-education-studio-landing.md) is Superseded. Monolith decomposition of src/web/static/modules/studios/education.js remains the wrong first build. File retained for history.

---

## 1. Four Beats

### Beat 1: What Jacob Means
1. Dig back into **Education Studio** after the Tools / Agent-builder wave.
2. First slice is hygiene, not new pedagogy: split the Education frontend monolith so Learning OS work is maintainable.
3. Behavior stays identical (Ask, course chrome, quiz/SRS, labs, tutor, Open in Chat/Observe).
4. Reuse the unfinished CARD-400 split when it still matches tip — do not invent a second layout.

### Beat 2: What AutoReiv Does Now
1. On tip `881cb276`, `src/web/static/modules/studios/education.js` is still one file (~2,569 lines), well over the 800-line hygiene limit (`.agents/rules/code-hygiene-and-pruning.md`).
2. Learning OS cards CARD-237..334 / 315..334 are Done on `qa`/`main` (course, ledger, retrieval, retention, tutor, amplifiers, delivery profiles).
3. Local branch `feat/card-400-education-monolith-decomposition` already extracts submodules and a thin coordinator, plus `tests/unit/frontend/education_monolith_decomposition_400.test.js`, but it was never merged and is far behind tip.
4. No Ready Education card existed after the v0.42.0 release.

### Beat 3: What Will Change
1. Cut `feat/card-434-education-monolith-decomposition` from current `qa`.
2. Port or rebase the CARD-400 decomposition onto tip so `education.js` is a thin coordinator and pedagogy lives under `src/web/static/modules/studios/education/`.
3. Keep public exports from `education.js` stable for existing Vitest / Playwright imports.
4. Contract tests assert submodule line caps and coordinator line cap; existing Education frontend tests stay green.
5. Live-test Education Studio on Jarvis (Ask mint + course chrome + one quiz path), then merge to local `qa` and push.

Target layout (from CARD-400 tip; adjust only if tip conflicts force it):

| Module | Role | Line cap |
| --- | --- | --- |
| `education.js` | Root coordinator (`initEducationStudio`), re-exports | < 1,000 |
| `education/course.js` | Course chrome, mastery, depth, delivery profiles | < 800 |
| `education/sessions.js` | Session list / localStorage / Open in Chat/Observe | < 800 |
| `education/ask.js` | Ask builder, SSE drain, HITL/job chrome forward | < 800 |
| `education/quiz.js` | Retrieval, SRS due, local grade, learner pressure | < 800 |
| `education/labs.js` | Construction / application labs shell | < 800 |
| `education/elaboration.js` | Feynman / explain-it-back | < 800 |
| `education/dual_coding.js` | Dual-coding Mermaid path | < 800 |
| `education/amplifiers.js` | Visual amplifiers / Lumina bridge chrome | < 800 |
| `education/analysis.js` | Metacog / error-log panel | < 800 |
| `education/environment.js` | Delivery / environment profile chrome | < 800 |
| `education/tutor.js` | Socratic tutor discuss entry | < 800 |

### Beat 4: What Dies Today
0. **This card itself is superseded by CARD-435** — do not implement the decomposition below.
1. The single ~2,569-line inlined Education Studio module body.
2. The stale CARD-400 "In Review" story on a branch that never landed — historical only under CARD-434 which is now superseded by CARD-435 (do not merge CARD-400 or CARD-434 decomposition as the Education first build).
3. No Learning OS pedagogy engines, ledger schema, or Tutor pack behavior changes on this card.

---

## 2. Acceptance Criteria (EARS)

- **Ubiquitous**: THE SYSTEM SHALL keep every file under `src/web/static/modules/studios/education/*.js` under 800 lines.
- **Ubiquitous**: THE SYSTEM SHALL keep `src/web/static/modules/studios/education.js` under 1,000 lines.
- **Ubiquitous**: THE SYSTEM SHALL preserve backward-compatible exports from `src/web/static/modules/studios/education.js` used by existing frontend tests.
- **Event-driven**: WHEN the operator runs Education Ask, jumps a course step, grades a quiz, or opens a session in Chat/Observe, THE EDUCATION STUDIO SHALL behave the same as tip before this card.
- **Negative**: Automated tests SHALL fail if any education submodule exceeds 800 lines or the coordinator exceeds 1,000 lines.
- **Proof**: `npm run test:unit:frontend` (Education-related suites including the decomposition contract) green; Jarvis live smoke of Ask + course chrome + one quiz grade path.

---

## 3. Constraints

- Branch off `qa` only: `feat/card-434-education-monolith-decomposition`.
- Prefer porting `ed1f6a6f` with conflict resolution against tip — do not drop contract tests.
- No pedagogy feature adds, no ledger schema changes, no Tutor pack rewrite.
- Do not merge to `qa` until Jacob says **merge to qa** after live test.
- After merge, delete local `feat/card-434-*` and the leftover `feat/card-400-education-monolith-decomposition`.

---

## 4. Reply Phrases

- Scaffold review: say **continue** if the Four Beats need edits.
- Start implementation: say **build**.
- After live test: say **merge to qa**.
