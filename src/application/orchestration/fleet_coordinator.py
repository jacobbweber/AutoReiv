"""
Fleet Coordination Protocol and Scoped Homelab Lookup Tools [CARD-198, REQ-FLEET-006, REQ-FLEET-007].
Orchestrates delegated specialist handoffs and structured knowledge retrieval across the Homelab Fleet.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

HOMELAB_FLEET_ROLES: Dict[str, str] = {
    "architect": "homelab-architect",
    "homelab-architect": "homelab-architect",
    "engineer": "homelab-engineer",
    "homelab-engineer": "homelab-engineer",
    "admin": "homelab-admin",
    "homelab-admin": "homelab-admin",
    "sysadmin": "homelab-admin",
    "janitor": "homelab-janitor",
    "homelab-janitor": "homelab-janitor",
}

CATEGORY_DIR_MAP: Dict[str, str] = {
    "governance": "00-governance",
    "00-governance": "00-governance",
    "network": "10-network",
    "10-network": "10-network",
    "compute": "20-compute",
    "20-compute": "20-compute",
    "identity": "30-identity",
    "30-identity": "30-identity",
    "services": "40-services",
    "40-services": "40-services",
    "runbooks": "50-runbooks",
    "50-runbooks": "50-runbooks",
    "templates": "templates",
}

FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", re.DOTALL)


def get_homelab_docs_root(base_dir: Optional[Path | str] = None) -> Path:
    """Resolve the canonical notes/homelab directory."""
    if base_dir is not None:
        p = Path(base_dir)
        if (p / "notes" / "homelab").is_dir():
            return p / "notes" / "homelab"
        return p
    from src.infrastructure.data.resolver import repo_root

    root = repo_root()
    return root / "notes" / "homelab"


def lookup_homelab_docs(
    query: Optional[str] = None,
    category: Optional[str] = None,
    doc_type: Optional[str] = None,
    notes_root: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """
    Search and retrieve enterprise IT homelab documentation from notes/homelab/.

    Use when:
    - Looking up VLAN numbers, IPAM subnet allocations, or DNS records.
    - Inspecting physical Hyper-V host capacity, switch names, or VM catalog.
    - Querying port reservations or Standard Operating Procedures (SOPs).

    Do not use when:
    - Searching general non-homelab Wiki notes outside notes/homelab/.
    """
    root = get_homelab_docs_root(notes_root)
    if not root.is_dir():
        return {
            "status": "error",
            "error": f"Homelab documentation directory not found at {root}",
            "documents": [],
        }

    search_dirs: List[Path] = []
    if category:
        cat_key = category.strip().lower()
        sub_name = CATEGORY_DIR_MAP.get(cat_key, cat_key)
        target_dir = root / sub_name
        if target_dir.is_dir():
            search_dirs.append(target_dir)
        else:
            # Fallback: check if matches any folder
            for d in root.iterdir():
                if d.is_dir() and cat_key in d.name.lower():
                    search_dirs.append(d)
    if not search_dirs:
        search_dirs = [d for d in root.iterdir() if d.is_dir()]

    matched_docs: List[Dict[str, Any]] = []
    q_lower = query.strip().lower() if query else None
    type_lower = doc_type.strip().lower() if doc_type else None

    for s_dir in search_dirs:
        for md_file in sorted(s_dir.glob("*.md")):
            try:
                raw_text = md_file.read_text(encoding="utf-8")
            except OSError as err:
                logger.warning("Failed to read %s: %s", md_file, err)
                continue

            metadata: Dict[str, Any] = {}
            body = raw_text
            fm_match = FRONTMATTER_RE.match(raw_text)
            if fm_match:
                try:
                    metadata = yaml.safe_load(fm_match.group(1)) or {}
                except Exception:
                    metadata = {}
                body = fm_match.group(2)

            if type_lower and str(metadata.get("doc_type", "")).lower() != type_lower:
                continue

            if q_lower:
                in_name = q_lower in md_file.name.lower()
                in_meta = any(q_lower in str(v).lower() for v in metadata.values())
                in_body = q_lower in body.lower()
                if not (in_name or in_meta or in_body):
                    continue

            rel_path = md_file.relative_to(root.parent)
            matched_docs.append(
                {
                    "path": str(rel_path).replace("\\", "/"),
                    "filename": md_file.name,
                    "metadata": metadata,
                    "content": body.strip(),
                }
            )

    return {
        "status": "success",
        "count": len(matched_docs),
        "documents": matched_docs,
    }


class FleetCoordinator:
    """
    Coordinates task delegation across the specialized Homelab Agent Fleet [REQ-FLEET-007].
    Injects relevant enterprise IT notes context into specialist handoffs.
    """

    def __init__(self, handoff_handler: Optional[Any] = None) -> None:
        self.handoff_handler = handoff_handler

    async def _execute_handoff(
        self,
        target_agent_id: str,
        task_directive: str,
        input_payload: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute handoff using provided handler or orchestration tools."""
        if self.handoff_handler is not None:
            return await self.handoff_handler(
                target_agent_id=target_agent_id,
                task_directive=task_directive,
                input_payload=input_payload,
            )
        from src.application.skills.orchestration_tools import OrchestrationTools

        tools = OrchestrationTools()
        return await tools.handoff_to_agent(
            target_agent_id=target_agent_id,
            task_directive=task_directive,
            input_payload=input_payload,
        )

    async def delegate_to_fleet_agent(
        self,
        specialist_role: str,
        task_directive: str,
        wiki_context_paths: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Delegate a specialized infrastructure task to an internal fleet specialist.

        Args:
            specialist_role: Target fleet role ('architect', 'engineer', 'admin', 'janitor')
            task_directive: Specific, actionable instruction for the specialist
            wiki_context_paths: Optional list of note paths under notes/homelab/ to inject
            parameters: Structured parameters, attributes, or variables

        Returns:
            Dict containing status, target_agent_id, and handoff execution results.
        """
        clean_role = (specialist_role or "").strip().lower()
        target_id = HOMELAB_FLEET_ROLES.get(clean_role)
        if not target_id:
            return {
                "status": "error",
                "error": (
                    f"Unknown specialist role '{specialist_role}'. "
                    f"Expected one of: {list(HOMELAB_FLEET_ROLES.keys())}"
                ),
            }

        # Collect documentation context if requested
        injected_notes: Dict[str, Any] = {}
        if wiki_context_paths:
            root = get_homelab_docs_root()
            for doc_rel in wiki_context_paths:
                clean_rel = doc_rel.strip().replace("notes/homelab/", "").replace("homelab/", "")
                fpath = root / clean_rel
                if fpath.is_file():
                    try:
                        injected_notes[clean_rel] = fpath.read_text(encoding="utf-8")
                    except OSError as err:
                        logger.warning("Failed to inject note %s: %s", fpath, err)

        payload: Dict[str, Any] = {
            "parameters": parameters or {},
            "injected_notes_count": len(injected_notes),
            "notes_context": injected_notes,
        }

        # Augment directive with injected notes notice if present
        augmented_directive = task_directive
        if injected_notes:
            notes_summary = ", ".join(injected_notes.keys())
            augmented_directive = (
                f"{task_directive}\n\n"
                f"[Fleet Context]: The following homelab documentation sheets are injected: {notes_summary}."
            )

        handoff_result = await self._execute_handoff(
            target_agent_id=target_id,
            task_directive=augmented_directive,
            input_payload=payload,
        )

        return {
            "status": "success",
            "target_agent_id": target_id,
            "result": handoff_result,
        }
