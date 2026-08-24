"""
Command Safety Guardrail Engine [REQ-GUARD-002, REQ-GUARD-003].
Evaluates CLI commands and script executions to intercept destructive commands,
pipe-to-shell payloads, fork bombs, and workspace path traversals.
"""


import os
import re
from typing import List, Optional

from src.domain.safety.models import CommandSafetyReport, RiskLevel, SafetyViolation

# Destructive and dangerous command patterns
CRITICAL_PATTERNS = [
    # Recursive root/wildcard filesystem wipes
    (
        r"\brm\s+.*(-[a-zA-Z]*r[a-zA-Z]*|--recursive).*\s+([/~*]|/\s*$|\.\s*$)",
        "RULE-DEST-001",
        "Destructive recursive deletion targeting root, home, or wildcards.",
    ),
    (
        r"\b(rmdir|rd|del)\s+.*(/[sS]).*\s+[cC]:\\",
        "RULE-DEST-002",
        "Destructive Windows recursive system directory wipe.",
    ),
    # Disk formatting and raw device overwrites
    (
        r"\bmkfs(\.[a-zA-Z0-9]+)?\b",
        "RULE-DISK-001",
        "Filesystem creation / disk wipe tool.",
    ),
    (
        r"\bformat\s+[a-zA-Z]:",
        "RULE-DISK-002",
        "Windows disk volume format command.",
    ),
    (
        r"\bdd\s+.*of=/dev/(sd[a-z]|nvme[0-9]|disk|hd[a-z])",
        "RULE-DISK-003",
        "Raw block device overwrite via dd.",
    ),
    # Remote pipe-to-shell execution
    (
        r"\b(curl|wget|fetch|iwr|Invoke-WebRequest)\b.*\|\s*(bash|sh|zsh|dash|powershell|cmd|python)",
        "RULE-NET-001",
        "Remote script download directly piped into shell interpreter.",
    ),
    # Fork bombs and runaway resource killers
    (
        r":\(\)\s*\{\s*:\|:&\s*\}\s*;\s*:",
        "RULE-BOMB-001",
        "Bash fork bomb execution pattern.",
    ),
    (
        r"%0\|%0",
        "RULE-BOMB-002",
        "Batch script fork bomb pattern.",
    ),
]

HIGH_PATTERNS = [
    # System shutdown and halt
    (
        r"\b(shutdown(\.exe)?|init\s+0|poweroff|halt)\b",
        "RULE-SYS-001",
        "Host system shutdown, poweroff, or halt command.",
    ),
    # Direct access to sensitive Linux security files
    (
        r"/etc/(shadow|passwd|sudoers|master\.passwd)\b",
        "RULE-TRAV-001",
        "Direct access to sensitive OS user credential database.",
    ),
    # Windows system directory modification attempts
    (
        r"(?i)[cC]:\\(Windows|WinNT)\\(System32|SysWOW64)\b",
        "RULE-TRAV-002",
        "Direct access or modification attempt targeting Windows System directory.",
    ),
]


class CommandGuardrail:
    """Deterministic security and safety guardrail engine for CLI execution."""

    @classmethod
    def check_path_traversal(
        cls,
        path: str,
        workspace_root: Optional[str] = None,
    ) -> Optional[SafetyViolation]:
        """
        Check if a file path escapes permitted workspace boundaries [REQ-SAFE-005].
        """
        clean_path = path.strip()

        # Check for direct sensitive system paths
        for pattern, rule_id, reason in HIGH_PATTERNS:
            if "TRAV" in rule_id and re.search(pattern, clean_path):
                return SafetyViolation(
                    rule_id=rule_id,
                    risk_level=RiskLevel.HIGH,
                    reason=reason,
                    matched_pattern=clean_path,
                )

        # Check for deep directory traversal sequences
        if re.search(r"(\.\.[/\\]){3,}", clean_path):
            return SafetyViolation(
                rule_id="RULE-TRAV-003",
                risk_level=RiskLevel.HIGH,
                reason="Deep directory traversal attempt escaping workspace.",
                matched_pattern=clean_path,
            )

        if workspace_root:
            abs_root = os.path.abspath(workspace_root)
            abs_target = os.path.abspath(os.path.join(abs_root, clean_path))
            if not abs_target.startswith(abs_root):
                return SafetyViolation(
                    rule_id="RULE-TRAV-004",
                    risk_level=RiskLevel.HIGH,
                    reason=f"Path '{clean_path}' escapes authorized workspace boundary '{workspace_root}'.",
                    matched_pattern=clean_path,
                )

        return None

    @classmethod
    def evaluate(
        cls,
        command: str,
        workspace_root: Optional[str] = None,
    ) -> CommandSafetyReport:
        """
        Evaluate a command string against destructive patterns and path traversal [REQ-SAFE-004].
        """
        clean_cmd = (command or "").strip()
        violations: List[SafetyViolation] = []

        # 1. Critical pattern evaluation
        for pattern, rule_id, reason in CRITICAL_PATTERNS:
            match = re.search(pattern, clean_cmd, re.IGNORECASE)
            if match:
                violations.append(
                    SafetyViolation(
                        rule_id=rule_id,
                        risk_level=RiskLevel.CRITICAL,
                        reason=reason,
                        matched_pattern=match.group(0),
                    )
                )

        # 2. High pattern evaluation
        for pattern, rule_id, reason in HIGH_PATTERNS:
            match = re.search(pattern, clean_cmd, re.IGNORECASE)
            if match:
                violations.append(
                    SafetyViolation(
                        rule_id=rule_id,
                        risk_level=RiskLevel.HIGH,
                        reason=reason,
                        matched_pattern=match.group(0),
                    )
                )

        # 3. Path traversal evaluation on command string
        trav_violation = cls.check_path_traversal(clean_cmd, workspace_root=workspace_root)
        if trav_violation:
            violations.append(trav_violation)

        # Determine overall safety status
        if any(v.risk_level == RiskLevel.CRITICAL for v in violations):
            highest_risk = RiskLevel.CRITICAL
            is_safe = False
        elif any(v.risk_level == RiskLevel.HIGH for v in violations):
            highest_risk = RiskLevel.HIGH
            is_safe = False
        elif any(v.risk_level == RiskLevel.MEDIUM for v in violations):
            highest_risk = RiskLevel.MEDIUM
            is_safe = True
        elif any(v.risk_level == RiskLevel.LOW for v in violations):
            highest_risk = RiskLevel.LOW
            is_safe = True
        else:
            highest_risk = RiskLevel.SAFE
            is_safe = True

        return CommandSafetyReport(
            command=clean_cmd,
            is_safe=is_safe,
            highest_risk=highest_risk,
            violations=violations,
        )

    @classmethod
    def is_safe(
        cls,
        command: str,
        workspace_root: Optional[str] = None,
    ) -> bool:
        """Convenience method returning True if command is safe to execute."""
        return cls.evaluate(command, workspace_root=workspace_root).is_safe
