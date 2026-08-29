# Design

Cards stay markdown. One skill. One status table. Existing HITL parks writes.

## Action to route to function

1. Chat / kernel tool call `list_cards` -> `CardSkill.list_cards` -> scan `{project_root}/.github/cards/CARD-*.md` -> parse frontmatter -> list of id, title, status, spec, rounds, path.
2. `read_card` / `write_card` -> jail under `{project_root}/.github/cards/` -> read or write UTF-8 markdown (HITL on write).
3. `set_card_status` -> parse card -> `CardStatusMachine.can_transition` -> update Status / return_reason / review_rounds -> rewrite frontmatter lines (HITL).
4. Discuss -> Ready: resolve Spec Reference under project_root; deny if the directory is missing or has none of requirements.md, design.md, tasks.md.
5. Returned: require `return_reason`; increment `review_rounds`. Returned -> In Progress denied when `review_rounds >= max_review_rounds`.
6. `read_spec` / `write_spec` -> jail under `{project_root}/docs/specs/<slug>/` (HITL on write).
7. `read_steering` -> AGENTS.md plus optional `.agents/**/*.md` and `.github/*.md` (not cards); return path, headings, excerpt (cap ~4k chars per file).
8. Omitted `project_root` -> `detect_autoreiv_root()` (walk for `.github/cards` + `AGENTS.md`). After CARD-085 this resolver will prefer the selected project.

## Frontmatter

Keep CARD-079 blockquote lines. Unknown keys are preserved. New keys are inserted after Spec Reference when missing.

## Out of this slice

Projects studio. File jail tools. Conductor / Review builtins. Git. GitHub issues. UI.
