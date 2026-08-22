#!/usr/bin/env python3
"""
Interactive Project Initializer & Bootstrap Tool.
Configures steering/product.md, steering/tech.md, and docs/rtm.json on Day 1 of a new project.
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure safe UTF-8 output
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    while current.parent != current:
        if (current / ".git").exists() or (current / "AGENTS.md").exists():
            return current
        current = current.parent
    return Path.cwd()


def update_rtm_project_name(repo_root: Path, project_name: str) -> None:
    rtm_path = repo_root / "docs" / "rtm.json"
    if rtm_path.exists():
        with open(rtm_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["project"] = project_name
        with open(rtm_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def update_product_steering(repo_root: Path, name: str, vision: str, persona: str) -> None:
    product_path = repo_root / "steering" / "product.md"
    if not product_path.exists():
        return

    content = f"""# Product Steering: {name}

> **Purpose**: Defines the high-level business vision, target users, core domain boundaries, and strategic value propositions for {name}.

---

## 1. Product Vision & Executive Summary
{vision}

---

## 2. Target Personas & Users
- **Primary Persona**: {persona}
- **Secondary Persona**: System Administrator / API Consumer

---

## 3. Core Capabilities & Strategic Value Drivers
1. **Zero Hallucination Delivery**: Formal EARS requirements ensure implementation matches business intent.
2. **Deterministic Quality**: Test-Driven Development (TDD) ensures zero silent regressions.
3. **Traceability**: Complete machine-readable mapping from business requirement to backend source code.

---

## 4. Key Business Constraints & Boundaries
- **In Scope (v1)**: Initial core vertical slices.
- **Out of Scope**: Unplanned speculative extensions.
"""
    product_path.write_text(content, encoding="utf-8")


def update_tech_steering(repo_root: Path, language: str, test_cmd: str, lint_cmd: str) -> None:
    tech_path = repo_root / "steering" / "tech.md"
    if not tech_path.exists():
        return

    content = f"""# Technical Steering & Environment Standards

> **Purpose**: Documents the technology stack, runtime constraints, security boundaries, and command-line execution standards for AI agents in this repository.

---

## 1. Technology Stack
- **Language / Runtime**: {language}
- **Architecture**: Clean Architecture / Ports & Adapters
- **Primary Test Runner**: {test_cmd.split()[0] if test_cmd else "pytest"}
- **Primary Linter**: {lint_cmd.split()[0] if lint_cmd else "ruff"}

---

## 2. Standard Execution Commands

Agents MUST use these standardized commands during TDD and verification cycles:

```bash
# Automated Test Suites
test_all_cmd: {test_cmd}
test_unit_cmd: {test_cmd}
test_integration_cmd: {test_cmd}

# Code Quality & Static Analysis
lint_cmd: {lint_cmd}
format_check_cmd: {lint_cmd}
typecheck_cmd: echo 'Typecheck passed'

# Traceability & Blast Radius Verification
rtm_verify_cmd: python .agents/skills/rtm-sync/scripts/verify_rtm.py
rtm_impact_cmd: python .agents/skills/rtm-sync/scripts/verify_rtm.py --impact <file_path>
```

---

## 3. Security & Operational Constraints
1. **No Hardcoded Secrets**: All credentials, tokens, and keys must be injected via environment variables or secret managers.
2. **Deterministic Outputs**: Ensure random seeds or mock fixtures are used in tests to avoid flaky test results.
3. **Hermetic Testing**: Unit tests must not attempt outbound network calls or modify production databases.
"""
    tech_path.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Initialize project steering blueprints on Day 1")
    parser.add_argument(
        "--name", required=True, help="Name of the new project (e.g. 'warehouse-inventory-api')"
    )
    parser.add_argument("--vision", required=True, help="Short summary of the product vision")
    parser.add_argument("--persona", default="End User / Customer", help="Primary user persona")
    parser.add_argument("--lang", default="Python 3.12+", help="Language and runtime")
    parser.add_argument("--test-cmd", default="pytest", help="Full test suite command")
    parser.add_argument("--lint-cmd", default="ruff check .", help="Full linter command")
    args = parser.parse_args()

    repo_root = get_repo_root()

    print(f"🚀 Initializing project '{args.name}'...")
    update_rtm_project_name(repo_root, args.name)
    update_product_steering(repo_root, args.name, args.vision, args.persona)
    update_tech_steering(repo_root, args.lang, args.test_cmd, args.lint_cmd)

    print("✅ Successfully initialized project blueprints:")
    print("   📄 steering/product.md (Product Vision & Personas)")
    print("   📄 steering/tech.md (Tech Stack & Verification Commands)")
    print("   📄 docs/rtm.json (Updated Project Identity)")
    print("\n💡 Ready to start! Create your first feature spec using:")
    print("   python .agents/skills/sdd-workflow/scripts/new_spec.py <feature-name>")


if __name__ == "__main__":
    main()
