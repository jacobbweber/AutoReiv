---
name: ui-review
description: Open on any card that changes what the operator sees. Checklist in order structure, interaction, polish.
---
# UI review

Fix in this order. Never polish over a broken structure or interaction.

## 1. Structure
- [ ] One control per operator job. No second button, picker or menu for the same job.
- [ ] One primary action per panel; the rest are visibly secondary.
- [ ] The operator can always tell which studio, agent, chat and job they are in.
- [ ] It works at phone width (390x844): no horizontal overflow; rows wrap to two lines.

## 2. Interaction (while the app is busy)
- [ ] While streaming or running, the operator can still read, scroll, cancel and approve.
- [ ] Autoscroll follows only when at the bottom; scrolling up shows "Jump to latest".
- [ ] Status is honest: never Done while work is running; failures say why.
- [ ] Every surface has loading, empty, error and success states that say what to do next.
- [ ] Every click gives visible feedback.
- [ ] Approvals appear where the work started, with enough context to decide.
- [ ] Destructive actions ask first.
- [ ] Leaving and coming back (reload, other device) returns to the same job.
- [ ] Badges only for things that need action; ambient state is a quiet dot.

## 3. Polish
- [ ] Spacing, radius and colour come from existing CSS variables, not new literals.
- [ ] Nested rounded boxes: outer radius = inner radius + padding.

Prove structure and interaction items with journey steps (`clickExpect`, visible-state assertions), not screenshots alone.
