---
name: sdd-workflow
description: >-
  Executes the Card-Driven Development workflow: Socratic requirement discovery, work card intake, Four Beats alignment, drafting EARS acceptance criteria, wireframes, and API contracts. Use whenever authoring a new feature, planning a card, or initializing a new repository.
---

# Card-Driven Development Workflow

Follow this procedure to specify any feature or change with zero hallucination and low cognitive load for Jacob.

---

## Phase 0: Day 1 Project Initialization (New Projects Only)

When creating a brand-new application from this template, run the bootstrap initializer:

```bash
python .agents/skills/sdd-workflow/scripts/init_project.py --name "<project-name>" --vision "<short product vision>" --persona "<primary persona>" --lang "<language>"
```

This automatically configures `steering/product.md` and `steering/tech.md` with your project's identity.

---

## Phase 1: Work Card Intake (Mandatory First Step)

Every product change begins with a ready-to-build work card:

```bash
python .agents/skills/sdd-workflow/scripts/new_card.py "<feature-title>" --intent "<why>" --what "<what to build>"
```

_Example_: `python .agents/skills/sdd-workflow/scripts/new_card.py "LLM Provider Settings" --intent "Configure local Ollama and cloud OpenAI API URLs" --what "Settings UI inputs and POST endpoint"`

1. Refine the generated `docs/cards/CARD-xxx.md` with Jacob.
2. Ensure the active plan artifact (`implementation_plan.md`) is **quarantined to this single card only**.

---

## Phase 2: Socratic Discovery & The Four Beats

Present the Four Beats to Jacob before code:

1. **What Jacob means**: The core product intent and user experience goal.
2. **What AutoReiv does now**: The current code path, DOM structure, and behavior.
3. **What will change**: The technical modifications and new primitives to be introduced.
4. **What dies today (The Prune List)**: The explicit, non-empty list of retired functions, variables, routes, DOM elements, or styles.

Clarify ambiguity with structured hypotheses and recommended trade-offs (Rule 1 of `human-engagement`).

---

## Phase 3: Visual Wireframe or API Contract

1. For frontend features: provide an **ASCII UI Wireframe** showing layout, primary vs secondary controls, and interactive states.
2. For backend features: provide a **Markdown API Contract** detailing endpoints, request payloads, response structures, and HTTP status codes.
3. Validate domain boundaries: confirm what is **In Scope** vs **Out of Scope**.

---

## Phase 4: Populate EARS Acceptance Criteria

In the card's Acceptance Criteria section (`docs/cards/CARD-xxx.md`), formulate all criteria using formal EARS syntax:

- Ubiquitous: `THE SYSTEM SHALL <action>`
- Event-driven: `WHEN <trigger> THE SYSTEM SHALL <action>`
- State-driven: `WHILE <state> THE SYSTEM SHALL <action>`
- Optional: `WHERE <feature enabled> THE SYSTEM SHALL <action>`
- Complex/Error: `WHEN <invalid condition> THE SYSTEM SHALL <action>`

---

## Phase 5: Human Build Gate (Strict Stop Gate)

1. Present the completed card and wireframe/contract to Jacob.
2. **DO NOT write production code** until Jacob explicitly replies with **build**.
