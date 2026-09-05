# [CARD-170] Desktop AI Companion Mascot and Modern Virtual Pet Mechanics

> **Status**: Ready
> **Created**: 2026-09-05
> **Spec Reference**: docs/specs/companion-mascot/
> **Labels**: `type:feature`, `AutoReiv.Companion`, `AutoReiv.Frontend`, `AutoReiv.Mascot`

---

## 1. Why / Intent

AI developer tools are often sterile and utilitarian. In the 2026 AI era, autonomous agents perform heavy lifting in the background, but the human-AI relationship can be playful, engaging, and alive.

This card introduces a modernized **Desktop AI Companion & Virtual Pet** that doubles as the official **AutoReiv Platform Mascot**. It gives the control plane a living personality: a reactive digital buddy that lives alongside the operator, reflects system health and task milestones, learns from conversations, and whose appearance and character design can be customized directly by the operator.

---

## 2. Core Mechanics & Architecture

### A. Living Telemetry & Pet Vitality ("Feeding on Productivity")
- Rather than artificial timers, the companion's mood, energy, and happiness dynamically bind to AutoReiv's platform events:
  - **Energy & Happiness**: Boosted when chat sessions solve problems, routines succeed, or the Training Lab promotes a new tool.
  - **Curious / Analytical**: Enters an investigative pose when the agent is executing background tool loops or sandbox tests.
  - **Drowsy / Rest**: Slumbers softly when the platform is idle or during late-night hours (America/New_York).
  - **Concerned**: Reacts with a diagnostic bubble if an unhandled error or routine failure occurs, offering a one-click shortcut to check system logs.

### B. User-Driven Character & Mascot Design
- The operator can customize and evolve the mascot's aesthetic:
  - **Form Factor**: Choose visual styles (e.g. Retro Cybernetic Sprite, Clean Vector Robot, Bioluminescent Orb).
  - **Accessories & Badges**: Unlockable hats, tools, and badges earned through system achievements (e.g. "100 Routine Executions", "First Hyper-V VM Provisioned", "Zero-Collision Tool Battery").
  - **Personality / Voice Directive**: Configurable tone directive mapped to the platform's Tone Registry (`companion_tone`).

### C. Cognitive Memory & Long-Term Bonding
- Uses AutoReiv's dedicated per-agent memory brain (`mascot_memory.db` under `packs/mascot/`):
  - Remembers operator preferences, recurring projects, and celebratory milestones.
  - Pops up witty, context-aware encouragement or timely reminders during long work sessions.

### D. Ergonomic UI Presentation
- **Workbench Dock**: Sits unobtrusively in the slim navigation rail or bottom-right workbench canvas with collapsible visibility.
- **Animations**: Built entirely with lightweight SVG, CSS keyframe transformations, and HTML5 canvas—zero heavy 3D game engines or GPU overhead.
- **Interactive Micro-Gestures**: Click to pet (happy animation + micro-toast message), double-click to open mascot customization drawer.

---

## 3. What to Build

### A. Companion State Engine (`src/application/companion/`)
- `CompanionStateService`: Aggregates real-time event telemetry (routine passes, errors, chat completions) into a normalized happiness/energy state (0–100).
- SQLite table `companion_state` persisting level, XP, unlocked cosmetic items, and mood attributes.
- API endpoints:
  - `GET /api/companion/status` (current mood, energy, level, dialogue snippet).
  - `POST /api/companion/interact` (pet, poke, feed activity token).
  - `PUT /api/companion/customization` (update visual theme, skin, accessory).

### B. Frontend Mascot Widget (`src/web/static/modules/companion/`)
- Lightweight, floating/dockable mascot component with fluid SVG sprite animations (idle, happy, thinking, sleeping, alert).
- Speech bubble overlay for proactive nudges, milestone toasts, and quick action shortcuts.
- Mascot Customization modal/drawer in Settings Studio or Agent Studio.

---

## 4. Acceptance Criteria (Definition of Done)

- [ ] [REQ-PET-001] Companion state model tracks vitality, mood, and experience derived from real platform activity.
- [ ] [REQ-PET-002] Lightweight, responsive SVG/Canvas mascot widget renders in AutoReiv UI with fluid state animations.
- [ ] [REQ-PET-003] Proactive speech bubble displays context-aware status updates and cheer messages tied to agent tasks.
- [ ] [REQ-PET-004] Operator customization controls allow selecting mascot visual styles, accessories, and personality tone.
- [ ] [REQ-PET-005] Companion interactions and milestones persist into local SQLite store with zero external cloud dependencies.
- [ ] Automated tests pass cleanly via pytest and Vitest.

---

## 5. Constraints & Honor Flags

- Zero third-party brand/trademark names in card, UI, or repo artifacts.
- Lightweight assets only (SVG / CSS) with zero performance degradation to the main workbench canvas.

