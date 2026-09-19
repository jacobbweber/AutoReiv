# Technical Design: DotAgents and Kiro Standardization Under .agents Directory

## C4 Context & Architecture Overview

The `.agents/` directory standard brings together the **DotAgents Protocol** (`https://dotagentsprotocol.com/`) for agent configuration and the **AWS Kiro** framework for spec-driven engineering.

```
+-----------------------------------------------------------------------------------+
| Project Root                                                                      |
|                                                                                   |
|  .agents/                                                                         |
|  ├── agents.md             (DotAgents / AGENTS.md open standard)                 |
|  ├── mcp.json              (MCP tool servers)                                    |
|  ├── skills/               (Procedural skills)                                   |
|  ├── cards/                (AutoReiv work cards with Three Beats)                |
|  ├── specs/<feature-slug>/ (AWS Kiro 3-file specs)                               |
|  │   ├── requirements.md   (EARS user stories & acceptance criteria)             |
|  │   ├── design.md         (Technical architecture & contracts)                  |
|  │   └── tasks.md          (Testable vertical slices)                            |
|  ├── steering/             (AWS Kiro persistent steering documents)              |
|  │   ├── product.md        (Product vision & high-level capabilities)            |
|  │   ├── tech.md           (Tech stack & constraints)                            |
|  │   ├── structure.md      (Folder layout & naming conventions)                  |
|  │   └── roadmap.md        (Milestones & backlog)                                |
|  ├── adr/                  (Immutable Architecture Decision Records)             |
|  ├── rtm.json              (Requirements Traceability Matrix)                    |
|  └── templates/            (Standard card, spec, and ADR templates)              |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

## Directory Resolution Logic (`CardTools`)

```python
def _cards_dir(self, root: Path) -> Path:
    agents_cards = root / ".agents" / "cards"
    if agents_cards.is_dir():
        return jail_join(root, ".agents/cards")
    github_cards = root / ".github" / "cards"
    if github_cards.is_dir():
        return jail_join(root, ".github/cards")
    return jail_join(root, ".agents/cards")
```

## Error Handling & Path Jailing
All operations continue to use `jail_join(root, relative_path)` to ensure no directory traversal attacks can break out of the project root.
