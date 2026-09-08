# Requirements: DotAgents and Kiro Standardization Under .agents Directory

## User Stories & EARS Requirements

### 1. DotAgents Directory Scaffold
- **User Story**: As a software engineer using AutoReiv, I want new projects to scaffold a canonical `.agents/` folder conforming to the DotAgents Protocol and AWS Kiro framework, so that all agent configuration, steering, cards, and specifications live in a standardized, version-controlled structure.
- **[REQ-SDLC-060]**: When `ProjectsService.create_project()` is invoked, the system shall scaffold a canonical `.agents/` directory structure containing `.agents/cards/`, `.agents/specs/`, `.agents/steering/` (with initial `product.md`, `tech.md`, `structure.md`, and `roadmap.md`), `.agents/adr/`, and `.agents/templates/`.

### 2. Dual-Path Resolution with Backward Compatibility
- **User Story**: As an engineer working across existing and new codebases, I want `CardTools` to resolve cards, specs, and steering from `.agents/` while maintaining seamless fallback to `.github/` and `docs/`, so that older projects continue working without migration pressure.
- **[REQ-SDLC-061]**: When resolving work card, spec, and steering directories, `CardTools` shall prioritize `.agents/cards/`, `.agents/specs/`, and `.agents/steering/`, and shall fall back to `.github/cards/`, `docs/specs/`, and `steering/` if `.agents/` equivalents are absent.

### 3. Standardized Artifact Templates with Three Beats
- **User Story**: As an operator collaborating with the Developer agent, I want standard markdown templates for cards, specifications, and architecture decision records that embed the Three Beats operating instructions, so that generated artifacts are consistent, structured, and auditable.
- **[REQ-SDLC-062]**: The system shall provide standard templates under `templates/sdlc-project/.agents/templates/` (`card.template.md`, `requirements.template.md`, `design.template.md`, `tasks.template.md`, `adr.template.md`), embedding the Three Beats (What he means, What AutoReiv does now, What will change) and AWS Kiro EARS patterns.

### 4. Constitution and Invariant Documentation
- **User Story**: As an autonomous agent and software engineer, I want `AGENTS.md` to document the canonical `.agents/` paths, the DotAgents Protocol, and the AWS Kiro standards, so that agent turns adhere to these standards across the entire SDLC.
- **[REQ-SDLC-063]**: `AGENTS.md` shall define the DotAgents Protocol directory layout, AWS Kiro steering/specification standards, and the Three Beats operating rhythm as platform invariants.
