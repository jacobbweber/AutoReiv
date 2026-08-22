---
name: sdd-workflow
description: >-
  Executes the AWS Kiro-style Spec-Driven Development (SDD) workflow: Socratic requirement discovery, project bootstrapping, drafting EARS requirements.md, technical design.md, and vertical slice tasks.md. Use whenever authoring a new feature, planning an epic, or initializing a new repository.
---

# Spec-Driven Development (SDD) Workflow

Follow this procedure to specify any feature or change with zero hallucination and low cognitive load for the Human Visionary.

---

## Phase 0: Day 1 Project Initialization (New Projects Only)
When creating a brand-new application from this template, run the bootstrap initializer:
```bash
python .agents/skills/sdd-workflow/scripts/init_project.py --name "<project-name>" --vision "<short product vision>" --persona "<primary persona>" --lang "<language>"
```
This automatically configures `steering/product.md`, `steering/tech.md`, and `docs/rtm.json` with your project's identity.

---

## Phase 1: Socratic Requirements Discovery
1. Review user intent, GitHub issue description, or prompt.
2. Formulate clarifying questions using the **Hypothesis & Option** pattern:
   - Provide structured choices with clear trade-offs.
   - Designate one option as `(Recommended)` based on industry standards.
3. Validate domain boundary and confirm what is **In Scope** vs. **Out of Scope**.

---

## Phase 2: Deterministic Spec Scaffolding (Zero Token Waste)
Run the automated spec scaffolder to generate the 3-file spec from template:
```bash
python .agents/skills/sdd-workflow/scripts/new_spec.py <feature-name> --domain <DOMAIN>
```
*Example*: `python .agents/skills/sdd-workflow/scripts/new_spec.py user-auth --domain AUTH`

This deterministically initializes:
- `docs/specs/<feature-name>/requirements.md`
- `docs/specs/<feature-name>/design.md`
- `docs/specs/<feature-name>/tasks.md`

---

## Phase 3: Populate EARS Requirements & Architecture
1. In `requirements.md`, formulate all acceptance criteria using formal EARS syntax:
   - Ubiquitous: `THE SYSTEM SHALL <action>`
   - Event-driven: `WHEN <trigger> THE SYSTEM SHALL <action>`
   - State-driven: `WHILE <state> THE SYSTEM SHALL <action>`
   - Optional: `WHERE <feature enabled> THE SYSTEM SHALL <action>`
   - Complex/Error: `WHEN <invalid condition> THE SYSTEM SHALL <action>`
2. In `design.md`, detail component models (Ports & Adapters) and Mermaid sequence diagrams.
3. In `tasks.md`, structure fine-grained vertical slice checklists referencing `[REQ-xxx]`.

---

## Phase 4: Human Review Gate
1. Present the completed 3-file specification to the Human Visionary for review.
2. **DO NOT write production code** until the Human Visionary explicitly approves the spec.
