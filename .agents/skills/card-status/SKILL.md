---
name: card-status
description: >-
  Use when listing or summarizing work card statuses — parses docs/cards/CARD-*.md headers into a consistent table (id, title, status).
---

# Card status board

Coding-assistant skill (not an AutoReiv pack skill). Cards live under `docs/cards/`.

## Command

```bash
python .agents/skills/card-status/scripts/list_card_status.py
python .agents/skills/card-status/scripts/list_card_status.py --status Ready
python .agents/skills/card-status/scripts/list_card_status.py --json
```

Parses both `> **Status**: …` blockquote headers and YAML `status:` frontmatter.
