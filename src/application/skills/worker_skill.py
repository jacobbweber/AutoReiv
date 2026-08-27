"""
Context-Isolated Batch Worker Skill & Map-Reduce Engine [REQ-ART-003].
"""

import asyncio
import glob
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.wiki_skill import WikiSkill
from src.domain.memory.models import SessionArtifact
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class BatchWorkerSkill:
    """
    Executes massive context tasks (repository scans, multi-file audits, log reviews)
    by partitioning workloads across parallel isolated subagent worker loops in memory.
    Saves outputs as ephemeral session artifacts with automatic TTL and 1-click Wiki promotion.
    """

    def __init__(
        self,
        state_store: Optional[SQLiteStateStore] = None,
        wiki_skill: Optional[WikiSkill] = None,
        workspace_root: Union[str, Path] = ".",
    ):
        self.state_store = state_store
        self.wiki_skill = wiki_skill or WikiSkill()
        self.workspace_root = Path(workspace_root).resolve()

    def _discover_files(self, paths: Union[List[str], str]) -> List[Path]:
        """Resolve a glob pattern, directory, or list of file paths relative to workspace."""
        collected: List[Path] = []
        if isinstance(paths, str):
            pattern = paths.strip()
            # If pattern contains glob characters or is a directory
            full_pattern = str(self.workspace_root / pattern)
            matches = glob.glob(full_pattern, recursive=True)
            for m in matches:
                p = Path(m)
                if p.is_file():
                    collected.append(p)
            # If no matches with direct glob, check relative glob
            if not collected and not any(c in pattern for c in "*?[]"):
                direct_path = (self.workspace_root / pattern).resolve()
                if direct_path.is_file():
                    collected.append(direct_path)
                elif direct_path.is_dir():
                    for root, _, files in os.walk(direct_path):
                        for f in files:
                            collected.append(Path(root) / f)
        elif isinstance(paths, list):
            for item in paths:
                p = (self.workspace_root / item).resolve()
                if p.is_file():
                    collected.append(p)
                elif p.is_dir():
                    for root, _, files in os.walk(p):
                        for f in files:
                            collected.append(Path(root) / f)
                else:
                    matches = glob.glob(str(self.workspace_root / item), recursive=True)
                    for m in matches:
                        mp = Path(m)
                        if mp.is_file() and mp not in collected:
                            collected.append(mp)

        # Deduplicate and sort
        unique_paths = sorted(list({p for p in collected if p.is_file()}))
        return unique_paths

    async def _process_chunk_worker(self, chunk: List[Path], objective: str, worker_id: int) -> Dict[str, Any]:
        """Worker task running in isolated memory context to inspect a chunk of files."""
        findings = []
        for file_path in chunk:
            try:
                rel_path = file_path.relative_to(self.workspace_root).as_posix()
            except ValueError:
                rel_path = file_path.name

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                line_count = len(content.splitlines())
                char_count = len(content)

                # Heuristic analysis against objective
                matched_lines = []
                obj_keywords = [k.lower() for k in objective.split() if len(k) > 3]
                for idx, line in enumerate(content.splitlines()[:500], 1):
                    line_lower = line.lower()
                    if any(kw in line_lower for kw in obj_keywords):
                        matched_lines.append((idx, line.strip()))

                findings.append(
                    {
                        "file": rel_path,
                        "lines": line_count,
                        "size_bytes": char_count,
                        "highlights": matched_lines[:5],
                    }
                )
            except Exception as e:
                findings.append(
                    {
                        "file": rel_path,
                        "error": str(e),
                    }
                )

        return {
            "worker_id": worker_id,
            "processed_count": len(chunk),
            "findings": findings,
        }

    async def batch_worker_scan(
        self,
        session_id: str,
        paths: Union[List[str], str],
        objective: str,
        title: Optional[str] = None,
        chunk_size: int = 5,
    ) -> Dict[str, Any]:
        """
        Partition target files into parallel isolated worker chunks, aggregate results,
        and save as an ephemeral session artifact.
        """
        target_files = self._discover_files(paths)
        if not target_files:
            return {
                "success": False,
                "error": f"No matching files discovered for path pattern: {paths}",
                "item_count": 0,
            }

        # Partition into chunks
        chunks = [target_files[i : i + chunk_size] for i in range(0, len(target_files), chunk_size)]

        # Execute parallel in-memory worker tasks
        tasks = [self._process_chunk_worker(chunk, objective, idx + 1) for idx, chunk in enumerate(chunks)]
        worker_results = await asyncio.gather(*tasks)

        # Synthesize consolidated report
        doc_title = title or f"Batch Scan: {objective[:40]} ({len(target_files)} files)"
        summary_text = (
            f"Scan completed across {len(target_files)} files using {len(chunks)} parallel worker loops. "
            f"Objective: '{objective}'."
        )

        md_sections = [
            f"# {doc_title}\n",
            f"**Objective**: {objective}\n",
            f"**Files Scanned**: {len(target_files)} | **Parallel Workers**: {len(chunks)} | **Timestamp**: {datetime.now(timezone.utc).isoformat()}\n",
            "## Summary of Findings\n",
        ]

        total_highlights = 0
        for w_res in worker_results:
            for item in w_res["findings"]:
                file_name = item.get("file", "unknown")
                if "error" in item:
                    md_sections.append(f"- `❌ {file_name}`: Error reading file: {item['error']}")
                    continue

                highlights = item.get("highlights", [])
                total_highlights += len(highlights)
                if highlights:
                    md_sections.append(f"### 📄 `{file_name}` ({item.get('lines', 0)} lines)")
                    for line_no, text in highlights:
                        md_sections.append(f"- **Line {line_no}**: `{text}`")
                else:
                    md_sections.append(
                        f"- 📄 `{file_name}` ({item.get('lines', 0)} lines) — No direct matches for keywords."
                    )

        content_markdown = "\n".join(md_sections)

        # Persist to SQLite session_artifacts
        art_id = f"art_{uuid.uuid4().hex[:10]}"
        artifact = SessionArtifact(
            id=art_id,
            session_id=session_id,
            title=doc_title,
            content_type="text/markdown",
            content=content_markdown,
            summary=summary_text,
            item_count=len(target_files),
            is_pinned=False,
        )

        if self.state_store:
            self.state_store.save_artifact(artifact)

        return {
            "success": True,
            "artifact_id": art_id,
            "artifact_uri": f"artifact://{art_id}",
            "title": doc_title,
            "summary": summary_text,
            "item_count": len(target_files),
            "worker_count": len(chunks),
            "preview": summary_text,
        }

    def get_session_artifact(self, artifact_id: str) -> Dict[str, Any]:
        """Retrieve an artifact by its ID."""
        if not self.state_store:
            return {"success": False, "error": "State store not configured"}

        art = self.state_store.get_artifact(artifact_id)
        if not art:
            return {"success": False, "error": f"Artifact '{artifact_id}' not found"}

        return {
            "success": True,
            "artifact": {
                "id": art.id,
                "session_id": art.session_id,
                "title": art.title,
                "content_type": art.content_type,
                "content": art.content,
                "summary": art.summary,
                "item_count": art.item_count,
                "is_pinned": art.is_pinned,
                "expires_at": art.expires_at.isoformat() if art.expires_at else None,
                "created_at": art.created_at.isoformat() if art.created_at else None,
            },
        }

    def promote_artifact_to_wiki(
        self,
        artifact_id: str,
        wiki_slug: str,
        title: Optional[str] = None,
        category: str = "reports",
        domain: str = "general",
    ) -> Dict[str, Any]:
        """Promote an ephemeral session artifact into a permanent curated Wiki Vault note."""
        if not self.state_store:
            return {"success": False, "error": "State store not configured"}

        art = self.state_store.get_artifact(artifact_id)
        if not art:
            return {"success": False, "error": f"Artifact '{artifact_id}' not found"}

        note_title = title or art.title
        res = self.wiki_skill.create_wiki_note(
            title=note_title,
            content=art.content,
            domain=domain,
            topic=category,
            category=category,
            summary=art.summary,
            relative_path=f"{wiki_slug}.md" if not wiki_slug.endswith(".md") else wiki_slug,
        )

        if res.get("success"):
            # Automatically pin the source artifact
            self.state_store.pin_artifact(artifact_id, is_pinned=True)
            return {
                "success": True,
                "wiki_slug": wiki_slug,
                "path": res.get("path"),
                "artifact_id": artifact_id,
                "message": f"Artifact successfully promoted to Wiki Vault at '{wiki_slug}' and pinned.",
            }
        return res

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register batch worker and artifact tools into the scoped tool registry."""
        registry.register_tool(
            name="batch_worker_scan",
            description=(
                "Partition a massive list of files, directories, or logs across parallel isolated "
                "in-memory subagents and store the consolidated report as an ephemeral session artifact."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Active chat session ID",
                    },
                    "paths": {
                        "type": "string",
                        "description": "File glob pattern, directory path, or comma-separated list of files to scan",
                    },
                    "objective": {
                        "type": "string",
                        "description": "Extraction goal or analysis criteria for worker subagents",
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional title for the resulting artifact",
                    },
                },
                "required": ["session_id", "paths", "objective"],
            },
            handler=self.batch_worker_scan,
        )

        registry.register_tool(
            name="get_session_artifact",
            description="Fetch the full content, metadata, and summary of a session artifact by its ID.",
            parameters={
                "type": "object",
                "properties": {
                    "artifact_id": {
                        "type": "string",
                        "description": "Unique artifact identifier (e.g. art_9f82c)",
                    },
                },
                "required": ["artifact_id"],
            },
            handler=self.get_session_artifact,
        )

        registry.register_tool(
            name="promote_artifact_to_wiki",
            description="Promote an ephemeral session artifact into a permanent, curated note in the Wiki Vault.",
            parameters={
                "type": "object",
                "properties": {
                    "artifact_id": {
                        "type": "string",
                        "description": "Unique artifact identifier to promote",
                    },
                    "wiki_slug": {
                        "type": "string",
                        "description": "Target relative wiki slug/path, e.g. 'reports/security-audit'",
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional custom title for the permanent wiki note",
                    },
                    "category": {
                        "type": "string",
                        "description": "Wiki category (e.g. 'reports', 'audits', 'guides')",
                    },
                },
                "required": ["artifact_id", "wiki_slug"],
            },
            handler=self.promote_artifact_to_wiki,
        )
