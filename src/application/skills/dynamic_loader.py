"""
Dynamic Skill Manual Loader [REQ-MCP-005].
Discovers and parses markdown SKILL.md manuals with YAML frontmatter and embedded JSON schemas.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.domain.gateway.models import ToolDefinition


class DynamicSkillLoader:
    """Discovers and parses portable SKILL.md documents into executable tool manifests."""

    @classmethod
    def load_skill_from_markdown(cls, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse frontmatter and embedded tool JSON blocks from SKILL.md."""
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            return None

        text = p.read_text(encoding="utf-8")
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        meta: Dict[str, Any] = {}
        body = text
        if frontmatter_match:
            try:
                loaded = yaml.safe_load(frontmatter_match.group(1))
                meta = loaded if isinstance(loaded, dict) else {}
            except Exception:
                meta = {}
            body = text[frontmatter_match.end() :]

        tools: List[ToolDefinition] = []
        # Find JSON code blocks that define tools
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
    def scan_skills_directory(cls, directory: str) -> List[Dict[str, Any]]:
        """Scan directory tree for all SKILL.md manuals."""
        root = Path(directory)
        if not root.exists() or not root.is_dir():
            return []

        skills: List[Dict[str, Any]] = []
        for skill_file in root.glob("**/SKILL.md"):
            loaded = cls.load_skill_from_markdown(str(skill_file))
            if loaded:
                skills.append(loaded)

        return skills
