"""The project AGENTS.md contract [CARD-562].

A project's AGENTS.md holds facts about that repo under fixed `## ` headings. Tools read only these:
`## Checks` (the commands run_project_checks may run) and `## Branches` (the base branch).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

CONTRACT_SECTIONS = ("Project", "Run", "Checks", "Branches", "Cards", "Rules", "Don't touch")

_HEADING = re.compile(r"^##\s+(.+?)\s*$")
_CHECK_LINE = re.compile(r"^\s*[-*]\s*([A-Za-z][\w -]{0,30}?)\s*:\s*(.+?)\s*$")
_BASE_LINE = re.compile(r"base branch\s*:\s*`?([A-Za-z0-9._/-]+)`?", re.IGNORECASE)


@dataclass
class AgentsContract:
    sections: List[str] = field(default_factory=list)
    checks: Dict[str, str] = field(default_factory=dict)
    base_branch: Optional[str] = None

    @property
    def missing_sections(self) -> List[str]:
        have = {s.lower() for s in self.sections}
        return [s for s in CONTRACT_SECTIONS if s.lower() not in have]


def _norm_heading(text: str) -> str:
    return text.replace("\u2019", "'").strip().rstrip(":")


def parse_agents_md(text: str) -> AgentsContract:
    contract = AgentsContract()
    current = ""
    in_fence = False
    for line in (text or "").splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _HEADING.match(line)
        if m:
            current = _norm_heading(m.group(1))
            contract.sections.append(current)
            continue
        key = current.lower()
        if key == "checks":
            cm = _CHECK_LINE.match(line)
            if cm:
                cmd = cm.group(2).strip().strip("`").strip()
                if cmd and not cmd.startswith(("{{", "<")):  # template placeholders are not commands
                    contract.checks[cm.group(1).strip().lower()] = cmd
        elif key == "branches" and contract.base_branch is None:
            bm = _BASE_LINE.search(line)
            if bm:
                contract.base_branch = bm.group(1)
    return contract
