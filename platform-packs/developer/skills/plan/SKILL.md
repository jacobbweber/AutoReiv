---
name: Plan
description: Explore codebase, review steering, check backlog cards, and draft technical specifications and global ADRs.
---

# Plan

Explore the codebase in read-only mode, establish requirements, and formulate an implementation plan before modifying any code.

## Order

1. Review the active task, card (`read_card`, `list_cards`), or user prompt to extract core intent.
2. Review project rules, architectural boundaries, and guidelines (`read_steering`).
3. Explore relevant files and directories in read-only mode (`list_project_dir`, `read_project_file`).
4. Formulate the technical specification under `docs/specs/`:
   - Requirements with EARS notation and unique IDs (`[REQ-xxx]`).
   - Technical design, component interactions, and data models.
   - Sequential, testable task breakdown.
5. If the change introduces a structural architectural decision or pattern shift, author a global Architecture Decision Record in `docs/adr/`.
6. Present the proposed plan and three beats (what you see, what exists now, what will change) for review.

## Pitfalls

- Never edit or overwrite production code files during the planning phase.
- Do not make architectural assumptions without inspecting existing files first.
- Keep ADRs in the global `docs/adr/` directory rather than fragmenting across subfolders.

## Done-when

- The requirements, technical design, and task list are documented with zero ambiguity, ready for implementation.
