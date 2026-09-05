"""
Dynamic Skill Manual Loader [REQ-MCP-005] [REQ-DATA-009] [REQ-DATA-010].
Discovers and parses markdown SKILL.md manuals with YAML frontmatter and embedded JSON schemas.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from src.domain.gateway.models import ToolDefinition
from src.domain.skills.user_pack import UserSkillManifest

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n", re.DOTALL)


def _split_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter only. Body is returned uninterpreted."""
    frontmatter_match = _FRONTMATTER_RE.match(text)
    meta: Dict[str, Any] = {}
    body = text
    if frontmatter_match:
        try:
            loaded = yaml.safe_load(frontmatter_match.group(1))
            meta = loaded if isinstance(loaded, dict) else {}
        except Exception as exc:
            logger.warning("YAML parse error in SKILL frontmatter: %s", exc)
            meta = {}
        body = text[frontmatter_match.end() :]
    return meta, body


class DynamicSkillLoader:
    """Discovers and parses portable SKILL.md documents into executable tool manifests."""

    @classmethod
    def load_skill_from_markdown(cls, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse frontmatter and embedded tool JSON blocks from SKILL.md."""
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            return None

        text = p.read_text(encoding="utf-8")
        meta, body = _split_frontmatter(text)

        tools: List[ToolDefinition] = []
        json_blocks = re.findall(r"```json\s*\n(.*?)\n```", body, re.DOTALL)
        for block in json_blocks:
            try:
                data = json.loads(block)
                if isinstance(data, dict) and "name" in data and "parameters" in data:
                    tools.append(
                        ToolDefinition(
                            name=data["name"],
                            description=data.get("description", ""),
                            parameters=data.get("parameters", {}),
                        )
                    )
            except Exception:
                continue

        return {
            "name": meta.get("name", p.parent.name),
            "description": meta.get("description", ""),
            "author": meta.get("author", "Unknown"),
            "path": str(p),
            "tools": tools,
            "instructions": body.strip(),
        }

    @classmethod
    def list_skill_manifests(cls, directory: str) -> List[UserSkillManifest]:
        """Scan SKILL.md files and return frontmatter name + description + path only.

        Does not parse the markdown body or JSON tool blocks [REQ-DATA-010].
        """
        root = Path(directory)
        if not root.exists() or not root.is_dir():
            return []

        manifests: List[UserSkillManifest] = []
        skip_parts = {"snapshots", "_archive"}
        for skill_file in sorted(root.glob("**/SKILL.md")):
            try:
                rel_parts = skill_file.relative_to(root).parts
            except ValueError:
                rel_parts = skill_file.parts
            if any(part in skip_parts for part in rel_parts[:-1]):
                continue
            try:
                text = skill_file.read_text(encoding="utf-8")
            except OSError as exc:
                logger.warning("Skipping unreadable SKILL.md %s: %s", skill_file, exc)
                continue
            meta, _body = _split_frontmatter(text)
            name = meta.get("name")
            description = meta.get("description")
            if not isinstance(name, str) or not name.strip():
                logger.warning("Skipping %s: agentskills.io frontmatter name is required", skill_file)
                continue
            if not isinstance(description, str) or not description.strip():
                logger.warning("Skipping %s: agentskills.io frontmatter description is required", skill_file)
                continue
            try:
                pack_id = skill_file.parent.relative_to(root).as_posix()
            except ValueError:
                pack_id = skill_file.parent.name
            if pack_id in (".", ""):
                pack_id = skill_file.parent.name or name.strip()
            manifests.append(
                UserSkillManifest(
                    id=pack_id,
                    name=name.strip(),
                    description=description.strip(),
                    path=str(skill_file),
                )
            )
        return manifests

    @classmethod
    def scan_skills_directory(cls, directory: str) -> List[Dict[str, Any]]:
        """Scan directory tree for all SKILL.md manuals (full body + tools)."""
        root = Path(directory)
        if not root.exists() or not root.is_dir():
            return []

        skills: List[Dict[str, Any]] = []
        for skill_file in root.glob("**/SKILL.md"):
            loaded = cls.load_skill_from_markdown(str(skill_file))
            if loaded:
                skills.append(loaded)

        return skills
