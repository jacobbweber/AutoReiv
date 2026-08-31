# Design

Leading `---` ... `---` of simple KEY: VALUE lines is YAML frontmatter (CARD-001 shape). AutoReiv cards still start with `# [CARD-NNN]` and keep the existing blockquote parser.

`spec_slug_from_reference` already strips `docs/specs/`, so a YAML `spec: react-loop-powershell` resolves to `docs/specs/react-loop-powershell/`. `_spec_exists` is unchanged: directory exists and at least one of requirements/design/tasks.md.

`serialize_card_frontmatter` dispatches: YAML origin rewrites the YAML block in place (status key updated, original key order, body after the closing fence). Blockquote origin still uses `render_card_frontmatter`.

## Out of this slice

Converting live project cards to blockquote. Deleting CARD-002. PyYAML. Nested YAML documents.
