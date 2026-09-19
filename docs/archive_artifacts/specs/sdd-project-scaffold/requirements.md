# Requirements

- REQ-SDLC-050: `create_project` copies `templates/sdlc-project/` into `projects_root/<slug>` so AGENTS.md, docs/specs, .github/cards, CHANGELOG.md, VERSION, CONTRIBUTING.md, tests, and README exist.
- REQ-SDLC-053: Slug jail under projects_root. `create_project` is a registered tool and a high-risk HITL action. Studio create uses the same copy.
