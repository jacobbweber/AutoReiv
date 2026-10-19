# Where a repo keeps its conventions

Read every file below that exists. The first column is what to look for; the second is what it usually tells you.

## Agent and assistant instructions
| File | Tells you |
|---|---|
| `AGENTS.md` (root, and nested ones in sub-folders) | Cross-tool agent rules: build, test, style, do and don't |
| `CLAUDE.md`, `.claude/` | Claude Code rules (same idea as AGENTS.md) |
| `GEMINI.md`, `.gemini/` | Gemini CLI rules |
| `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md` | GitHub Copilot rules |
| `.cursor/rules/*.mdc`, `.cursorrules` | Cursor rules |
| `.windsurfrules`, `.clinerules` | Other assistants' rules |

If several exist, they usually agree; when they conflict, say so and ask the operator which wins.

## Project facts
| File | Tells you |
|---|---|
| `README.md`, `CONTRIBUTING.md`, `docs/` | Purpose, setup, contribution and review rules |
| `package.json` (`scripts`), `pnpm-workspace.yaml`, `turbo.json` | Node install, dev, build, test, lint commands |
| `pyproject.toml`, `requirements*.txt`, `uv.lock`, `tox.ini`, `noxfile.py` | Python tooling and test commands |
| `Makefile`, `justfile`, `Taskfile.yml` | Named tasks (often the canonical commands) |
| `Cargo.toml`, `go.mod`, `*.csproj`, `build.gradle` | Rust, Go, .NET, JVM builds |
| `project.godot`, `export_presets.cfg` | Godot game project and export targets |
| `Dockerfile`, `docker-compose.yml`, `.devcontainer/` | How it runs in containers |
| `.github/workflows/*.yml`, `.gitlab-ci.yml` | What CI runs (the most reliable test command) |
| `.editorconfig`, linter configs (`.eslintrc*`, `ruff.toml`, `.prettierrc`) | Style rules |

## Work tracking
| Place | Way of working |
|---|---|
| GitHub issues and PRs (use the GitHub MCP tools if mounted) | Issue-driven |
| `specs/`, `.specify/`, `docs/specs/` | Spec-driven (use `spec-driven-development`) |
| `.agents/cards/`, `docs/cards/` | Cards (use `project-cards`) |
| `docs/adr/`, `adr/` | Architecture decisions |
| `CHANGELOG.md` | Release notes style |

## Running commands
Use the commands you found (CI first, then Makefile or package scripts) with `cli_exec` from the `software-development`
skill. If the repo's `AGENTS.md` has a `## Checks` section, `run_project_checks` runs exactly those.
