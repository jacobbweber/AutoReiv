# Requirements

- REQ-SDLC-070: `parse_card_frontmatter` accepts YAML `---` simple `KEY: VALUE` `---` in addition to blockquote `> **Key**: value`. No PyYAML. Nested / list-only lines are ignored. If both formats are present, blockquote wins on conflict and YAML fills missing keys.
- REQ-SDLC-071: `CardFrontmatter.spec_reference` reads `Spec Reference`, `spec_reference`, or `spec` (case-insensitive). `status` reads `Status` or `status`.
- REQ-SDLC-072: Discuss -> Ready succeeds when the resolved spec slug exists as `docs/specs/<slug>/` with at least one of requirements.md, design.md, or tasks.md. YAML-origin cards keep YAML on `set_card_status` rewrite; AutoReiv cards stay blockquote. Body is preserved.
