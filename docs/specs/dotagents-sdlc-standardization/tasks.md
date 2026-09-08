# Tasks: DotAgents and Kiro Standardization Under .agents Directory

- [ ] Task 1: Update CardTools path resolution (`[REQ-SDLC-061]`)
  - [ ] 1.1: Add unit tests for `_cards_dir`, `_spec_dir`, and `_steering_dir` resolving `.agents/` with legacy `.github/` fallback.
  - [ ] 1.2: Implement `.agents/` resolution in `src/application/skills/card_tools.py`.
- [ ] Task 2: Update project template with canonical `.agents/` layout and templates (`[REQ-SDLC-060]`, `[REQ-SDLC-062]`)
  - [ ] 2.1: Add `.agents/steering/` (`product.md`, `tech.md`, `structure.md`, `roadmap.md`) to `templates/sdlc-project/`.
  - [ ] 2.2: Add `.agents/templates/` (`card.template.md`, `requirements.template.md`, `design.template.md`, `tasks.template.md`, `adr.template.md`) to `templates/sdlc-project/`.
  - [ ] 2.3: Update `REQUIRED_SCAFFOLD` in `src/application/sdlc/projects_service.py` and verify project creation unit tests.
- [ ] Task 3: Invariants, RTM sync, and DoD verification (`[REQ-SDLC-063]`)
  - [ ] 3.1: Update `AGENTS.md` with canonical path documentation.
  - [ ] 3.2: Sync `docs/rtm.json` with `REQ-SDLC-060` through `REQ-SDLC-063`.
  - [ ] 3.3: Run full test suite, linting, and verify DoD.
