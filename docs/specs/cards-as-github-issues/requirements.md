# Requirements

- REQ-SDLC-040: Status labels: status:discuss, status:ready, status:in-progress, status:in-review, status:returned, status:done.
- REQ-SDLC-041: Type labels come from the card Labels line (`type:feature` and similar).
- REQ-SDLC-042: `sync_card_issue` uses `gh` when present. Writes `github_issue` on the card after create/update. If `gh` is missing, return a clear error. HITL on the tool. Dry-run mode is for tests.
