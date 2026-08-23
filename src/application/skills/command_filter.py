"""
Dangerous Command Filter [REQ-SAFE-001].
Inspects CLI shell commands against prohibited destructive patterns.
"""

import re
from typing import List, Optional, Pattern, Tuple


class DangerousCommandFilter:
    """Static security analyzer for shell commands."""

    PROHIBITED_PATTERNS: List[Tuple[Pattern[str], str]] = [
        (re.compile(r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f*|-r|-f)\s+(/|/\*|~|~\*)(\s|$)", re.IGNORECASE), "Recursive root/home directory deletion (rm -rf /)"),
        (re.compile(r"\bmkfs(\.[a-zA-Z0-9]+)?\s+", re.IGNORECASE), "Filesystem format operation (mkfs)"),
        (re.compile(r"\bdd\s+.*of=/dev/(sd[a-z]|nvme[0-9]n[0-9]|hd[a-z]|disk[0-9])", re.IGNORECASE), "Raw block device overwriting (dd)"),
        (re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", re.IGNORECASE), "Fork bomb sequence"),
        (re.compile(r"\bformat\s+[a-zA-Z]:", re.IGNORECASE), "Windows disk partition format (format c:)"),
        (re.compile(r"\b(DROP\s+DATABASE|DROP\s+TABLE)\b", re.IGNORECASE), "Destructive SQL drop statement"),
        (re.compile(r"\b(fdisk|parted|gdisk)\s+", re.IGNORECASE), "Disk partitioning tool invocation"),
    ]

    @classmethod
    def is_dangerous(cls, cmd: str) -> Tuple[bool, Optional[str]]:
        """Check whether a command contains prohibited destructive patterns."""
        if not cmd:
            return False, None

        normalized = cmd.strip()
        for pattern, desc in cls.PROHIBITED_PATTERNS:
            if pattern.search(normalized):
                return True, f"Prohibited dangerous command: {desc}"

        return False, None
