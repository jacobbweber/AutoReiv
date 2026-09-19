---
name: card-status
description: >-
  Granular work card query, inspection, and status skill. Token-efficiently filters active cards by default, searches by keywords/labels, inspects single cards, and displays recent card history.
---

# Card Status & Query Board

Coding-assistant skill for querying, searching, and inspecting AutoReiv work cards under `docs/cards/`. Token-efficient by design: defaults to displaying active/actionable cards only rather than dumping historical backlogs.

---

## Commands & Recipes

### 1. Default Query (Active / Open Cards Only)

Prints a 1-line total breakdown and displays only cards in progress, ready for review, or ready to build:

```bash
python .agents/skills/card-status/scripts/list_card_status.py
```

### 2. Recent Cards (What Did We Just Finish?)

Shows the latest $N$ cards by card number (descending):

```bash
python .agents/skills/card-status/scripts/list_card_status.py --recent 5
python .agents/skills/card-status/scripts/list_card_status.py --latest 10
```

### 3. Single-Card Detail Inspector

Inspects a specific card, printing all metadata, file path, labels, ADRs, and the Beat 1 (Why / Intent) summary:

```bash
python .agents/skills/card-status/scripts/list_card_status.py --card 382
python .agents/skills/card-status/scripts/list_card_status.py --id CARD-381
```

### 4. Granular Search & Label Filtering

Search across card IDs, titles, labels, ADR references, and intent excerpts:

```bash
# Keyword search across all cards
python .agents/skills/card-status/scripts/list_card_status.py --search "wiki"
python .agents/skills/card-status/scripts/list_card_status.py -q "mcp"

# Filter by label or tag
python .agents/skills/card-status/scripts/list_card_status.py --label "type:bug"
python .agents/skills/card-status/scripts/list_card_status.py --tag "area:agents"
```

### 5. Status Filters

Filter specifically by card state:

```bash
python .agents/skills/card-status/scripts/list_card_status.py --status Ready
python .agents/skills/card-status/scripts/list_card_status.py --status "In Review"
python .agents/skills/card-status/scripts/list_card_status.py --parked
python .agents/skills/card-status/scripts/list_card_status.py --done
```

### 6. Full Backlog Dump & JSON Output

```bash
# Show all cards across entire history
python .agents/skills/card-status/scripts/list_card_status.py --all

# Machine-readable JSON
python .agents/skills/card-status/scripts/list_card_status.py --json
python .agents/skills/card-status/scripts/list_card_status.py --json --recent 5
```

---

## Metadata Support

Parses both YAML frontmatter (`--- ... ---`) and Markdown blockquote headers (`> **Key**: value`), supporting:

- `id`: Unique card identifier (`CARD-xxx`)
- `status`: Lifecycle state (`Ready`, `In Review`, `Done`, `Parked`, etc.)
- `created` / `completed`: ISO dates
- `labels` / `tags`: Comma-separated or YAML list
- `adr` / `adr_reference`: Architecture decision records
- `branch`: Git feature branch
- `intent`: Beat 1 (Why / Intent) excerpt
