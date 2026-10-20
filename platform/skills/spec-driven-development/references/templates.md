# Spec, plan and tasks templates

Use the repo's own templates when it has them (for example `.specify/templates/`). Otherwise use these.

## spec.md
```markdown
# <Feature name>

## Why
<The problem, who has it, and what changes for them.>

## User stories
- As a <who>, I want <what>, so that <why>.

## Acceptance criteria
- [ ] <Observable, checkable statement.>

## Out of scope
- <What this feature does not do.>

## Open questions
- [NEEDS CLARIFICATION: <question>]
```

## plan.md
```markdown
# Plan: <Feature name>

## Approach
<Architecture in a few sentences. A small diagram if it helps.>

## Stack and dependencies
<What is used and why. New dependencies are listed and approved by the operator.>

## Data and interfaces
<Models, files, endpoints, scenes or components that change.>

## Testing
| Acceptance criterion | Test (file and kind) |
|---|---|

## Risks
- <Risk and how it is handled.>
```

## tasks.md
```markdown
# Tasks: <Feature name>

- [ ] T001 <Write failing test for ...> (`path/to/test`)
- [ ] T002 <Make it pass: ...> (`path/to/file`)
- [ ] T003 [P] <Independent task that can run alongside T004>
```
