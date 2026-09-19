"""
Mechanical Capability Linter & Contract Compiler [CARD-363, ADR-0054].
Enforces static validation for SKILL.md runbooks: Rule of 7 tool budget,
mandatory verification contracts, and security boundary protection.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import yaml

from src.domain.skills.contract import (
    LintReport,
    LintSeverity,
    LintViolation,
    SafetyContract,
    SkillContract,
    VerificationContract,
    VerificationKind,
)

logger = logging.getLogger(__name__)

MAX_TOOLS_PER_SKILL = 6
MAX_RUNBOOK_BODY_CHARS = 8000

HIGH_RISK_TOOLS: frozenset[str] = frozenset(
    {
        "cli_exec",
        "repo_file_write",
        "repo_file_patch",
        "write_project_file",
        "execute_code",
        "execute_agent_database",
        "delete_file",
        "bash",
        "shell",
    }
)


class SkillContractCompiler:
    """Compiles raw SKILL.md text into a typed SkillContract and runs mechanical validation."""

    def compile(self, text: str, path: Optional[str] = None) -> Tuple[Optional[SkillContract], List[LintViolation]]:
        violations: List[LintViolation] = []
        path_str = str(path or "")

        frontmatter_dict, raw_body = self._parse_frontmatter_and_body(text)

        # Fallback to markdown parsing if frontmatter is missing
        name = frontmatter_dict.get("name") if frontmatter_dict else None
        if not name:
            header_match = re.search(r"^#\s+(.+)$", raw_body, re.MULTILINE)
            name = header_match.group(1).strip() if header_match else "Unnamed Skill"

        description = frontmatter_dict.get("description", "") if frontmatter_dict else ""
        version = str(frontmatter_dict.get("version", "1.0.0")) if frontmatter_dict else "1.0.0"

        # Resolve requires_tools
        requires_tools = self._resolve_tools(frontmatter_dict, raw_body)

        # Resolve verification contract
        verification = self._resolve_verification(frontmatter_dict, raw_body)

        # Resolve safety contract
        safety = self._resolve_safety(frontmatter_dict)

        contract = SkillContract(
            id=Path(path_str).parent.name if path_str else name.lower().replace(" ", "-"),
            name=name,
            description=description,
            version=version,
            requires_tools=requires_tools,
            verification=verification,
            safety=safety,
            raw_body=raw_body,
            path=path_str or None,
        )

        # Rule CAP-001: Tool Entropy Budget Cap (len(requires_tools) <= 6) [REQ-CAP-LINT-001]
        if len(contract.requires_tools) > MAX_TOOLS_PER_SKILL:
            violations.append(
                LintViolation(
                    rule_id="CAP-001",
                    rule_name="tool_budget_cap",
                    severity=LintSeverity.ERROR,
                    message=(
                        f"Tool budget exceeded: {len(contract.requires_tools)} tools declared, "
                        f"maximum allowed is {MAX_TOOLS_PER_SKILL}."
                    ),
                    path=path_str,
                )
            )

        # Rule CAP-002: Mandatory Deterministic Verification Contract [REQ-CAP-LINT-002]
        if contract.verification is None or not contract.verification.rule.strip():
            violations.append(
                LintViolation(
                    rule_id="CAP-002",
                    rule_name="mandatory_verification",
                    severity=LintSeverity.ERROR,
                    message="Missing completion verification contract or testable 'Done-when' criteria.",
                    path=path_str,
                )
            )

        # Rule CAP-003: Security Boundary Collision [REQ-CAP-LINT-003]
        if contract.safety.untrusted_input_allowed:
            mutating = [t for t in contract.requires_tools if t in HIGH_RISK_TOOLS]
            if mutating and not contract.safety.requires_hitl:
                violations.append(
                    LintViolation(
                        rule_id="CAP-003",
                        rule_name="security_boundary_collision",
                        severity=LintSeverity.ERROR,
                        message=(
                            f"Security boundary collision: untrusted input permitted with mutating tools "
                            f"({', '.join(mutating)}) without requires_hitl: true."
                        ),
                        path=path_str,
                    )
                )

        # Rule CAP-004: Runbook Markdown Body Size Budget [REQ-CAP-LINT-001]
        if len(contract.raw_body) > MAX_RUNBOOK_BODY_CHARS:
            violations.append(
                LintViolation(
                    rule_id="CAP-004",
                    rule_name="runbook_size_budget",
                    severity=LintSeverity.WARNING,
                    message=(
                        f"Runbook body exceeds 8,000 characters ({len(contract.raw_body)} chars). "
                        "Consider condensing to protect context budget."
                    ),
                    path=path_str,
                )
            )

        return contract, violations

    def _parse_frontmatter_and_body(self, text: str) -> Tuple[Dict[str, Any], str]:
        if not text.startswith("---"):
            return {}, text

        parts = text.split("---", 2)
        if len(parts) < 3:
            return {}, text

        frontmatter_str = parts[1]
        body = parts[2]
        try:
            parsed = yaml.safe_load(frontmatter_str) or {}
            if isinstance(parsed, dict):
                return parsed, body.strip()
        except Exception as exc:
            logger.debug("Failed to parse YAML frontmatter: %s", exc)

        return {}, body.strip()

    def _resolve_tools(self, frontmatter: Dict[str, Any], body: str) -> List[str]:
        raw_tools = frontmatter.get("requires_tools") or frontmatter.get("tools")
        if isinstance(raw_tools, (list, tuple)):
            return [str(t).strip() for t in raw_tools if str(t).strip()]

        # Markdown extraction fallback from `## Available Tools`
        extracted: List[str] = []
        tools_section = re.search(r"## Available Tools(.*?)(?:##|\Z)", body, re.DOTALL | re.IGNORECASE)
        if tools_section:
            section_text = tools_section.group(1)
            matches = re.findall(r"-\s+`([^`]+)`", section_text)
            for m in matches:
                name = m.strip()
                if name and name not in extracted:
                    extracted.append(name)

        return extracted

    def _resolve_verification(
        self, frontmatter: Dict[str, Any], body: str
    ) -> Optional[VerificationContract]:
        verif_data = frontmatter.get("verification")
        if isinstance(verif_data, dict) and verif_data.get("rule"):
            kind_str = str(verif_data.get("kind", "command")).lower().strip()
            try:
                kind = VerificationKind(kind_str)
            except ValueError:
                kind = VerificationKind.COMMAND
            return VerificationContract(
                kind=kind,
                rule=str(verif_data.get("rule", "")).strip(),
                expected_exit_code=int(verif_data.get("expected_exit_code", 0)),
                assert_pattern=verif_data.get("assert_pattern"),
            )

        # Markdown extraction fallback from `## Done-when` or `## Verification`
        match = re.search(
            r"## (?:Done-when|Verification)(.*?)(?:##|\Z)", body, re.DOTALL | re.IGNORECASE
        )
        if match:
            text = match.group(1).strip()
            if text:
                return VerificationContract(
                    kind=VerificationKind.ASSERTION,
                    rule=text,
                    expected_exit_code=0,
                )

        return None

    def _resolve_safety(self, frontmatter: Dict[str, Any]) -> SafetyContract:
        safety_data = frontmatter.get("safety")
        if isinstance(safety_data, dict):
            return SafetyContract(
                read_only=bool(safety_data.get("read_only", False)),
                requires_hitl=bool(safety_data.get("requires_hitl", False)),
                untrusted_input_allowed=bool(safety_data.get("untrusted_input_allowed", False)),
            )
        return SafetyContract()


class CapabilityLinter:
    """Scans filesystem paths for SKILL.md runbooks and generates an aggregated LintReport."""

    def __init__(self, compiler: Optional[SkillContractCompiler] = None) -> None:
        self.compiler = compiler or SkillContractCompiler()

    def lint_file(self, path: Union[str, Path]) -> Tuple[Optional[SkillContract], List[LintViolation]]:
        p = Path(path)
        if not p.is_file():
            return None, [
                LintViolation(
                    rule_id="IO-001",
                    rule_name="file_not_found",
                    severity=LintSeverity.ERROR,
                    message=f"File not found: {p}",
                    path=str(p),
                )
            ]
        try:
            content = p.read_text(encoding="utf-8")
        except Exception as exc:
            return None, [
                LintViolation(
                    rule_id="IO-002",
                    rule_name="read_error",
                    severity=LintSeverity.ERROR,
                    message=f"Error reading file: {exc}",
                    path=str(p),
                )
            ]

        return self.compiler.compile(content, path=str(p))

    def lint_paths(self, paths: Sequence[Union[str, Path]]) -> LintReport:
        target_files: List[Path] = []
        for raw_path in paths:
            p = Path(raw_path)
            if p.is_file() and p.name.lower() == "skill.md":
                target_files.append(p)
            elif p.is_dir():
                target_files.extend(p.glob("**/SKILL.md"))

        target_files = sorted(list(set(target_files)))
        scanned_count = len(target_files)
        all_violations: List[LintViolation] = []
        valid_count = 0

        for file_path in target_files:
            contract, violations = self.lint_file(file_path)
            errors = [v for v in violations if v.severity == LintSeverity.ERROR]
            if not errors:
                valid_count += 1
            all_violations.extend(violations)

        error_count = sum(1 for v in all_violations if v.severity == LintSeverity.ERROR)
        warning_count = sum(1 for v in all_violations if v.severity == LintSeverity.WARNING)

        return LintReport(
            scanned_count=scanned_count,
            valid_count=valid_count,
            error_count=error_count,
            warning_count=warning_count,
            violations=all_violations,
            passed=error_count == 0,
        )

    def lint_platform_and_user_skills(self, data_dir: Optional[Path] = None) -> LintReport:
        """Scan platform-packs/ seed directory and resolved user-data pack directories."""
        paths: List[Path] = []

        # Platform seed packs in repository
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        platform_packs_dir = repo_root / "platform-packs"
        if platform_packs_dir.exists():
            paths.append(platform_packs_dir)

        # User data packs directory
        from src.infrastructure.data.resolver import resolve_data_dir

        resolved_data = data_dir or resolve_data_dir()
        if resolved_data.exists():
            packs_dir = resolved_data / "packs"
            if packs_dir.exists():
                paths.append(packs_dir)
            skills_dir = resolved_data / "skills"
            if skills_dir.exists():
                paths.append(skills_dir)

        return self.lint_paths(paths)
