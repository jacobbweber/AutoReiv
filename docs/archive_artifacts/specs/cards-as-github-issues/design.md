# Design

No MCP. No tokens. `gh` or a clear miss.

## Action to route to function

1. `sync_card_issue` -> read card -> `github_label_map(status, labels_line)` -> if dry_run, return title/body/labels.
2. If `gh` missing -> `{success:false, error:"gh is not available..."}`.
3. If `github_issue` empty -> `gh issue create --title --body --label ...` -> write number on the card.
4. If present -> `gh issue edit <n> --title --body` and replace status labels.

Conductor allowlist stays 11. Tool is in the catalog.

## Out of this slice

git push. GitHub MCP. Multi-org routers.
