# Requirements

- REQ-SDLC-010: `set_card_status` enforces Discuss | Ready | In Progress | In Review | Returned | Done. Legal transitions only. Discuss -> Ready requires the Spec Reference path to exist. Returned stores `return_reason` and increments `review_rounds`. At `review_rounds` >= `max_review_rounds` (default 3), In Progress is denied and the tool tells the caller to ask the operator.
- REQ-SDLC-011: Card frontmatter parse/write supports Status, Spec Reference, review_rounds, max_review_rounds, return_reason, optional github_issue (blockquote `> **Key**: value` style used by CARD-079).
- REQ-SDLC-012: Tools operate on `{project_root}/.github/cards/CARD-NNN-*.md` and `{project_root}/docs/specs/<slug>/`. `project_root` is an optional argument defaulting to the AutoReiv checkout.
- REQ-SDLC-013: `list_cards`, `read_card`, `write_card`, `read_spec`, `write_spec`, `read_steering` are registered on the master tool registry. `read_steering` returns path + excerpt or headings for AGENTS.md and optional `.agents` / `.github` rules, not a huge dump.
- REQ-SDLC-014: `write_card`, `write_spec`, `set_card_status` are on the existing HITL high-risk list.
