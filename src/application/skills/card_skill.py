"""
Card, spec, and steering tools for the spec-driven SDLC loop [REQ-SDLC-010..014].
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.sdlc.paths import ProjectPathError, jail_join, resolve_project_root
from src.domain.sdlc.models import (
    CardStatusMachine,
    extract_card_id,
    extract_card_title,
    parse_card_frontmatter,
    render_card_frontmatter,
    spec_slug_from_reference,
)

STEERING_EXCERPT_CHARS = 4000
SPEC_FILENAMES = ("requirements.md", "design.md", "tasks.md")


class CardSkill:
    """Markdown cards + specs under a project_root. No second workflow engine."""

    def __init__(
        self,
        default_project_root: Optional[str] = None,
        root_resolver: Optional[Callable[[Optional[str]], Path]] = None,
    ):
        self._default_root = Path(default_project_root).resolve() if default_project_root else None
        self._root_resolver = root_resolver
        self._machine = CardStatusMachine()

    def _root(self, project_root: Optional[str] = None) -> Path:
        if self._root_resolver is not None:
            return Path(self._root_resolver(project_root)).resolve()
        return resolve_project_root(project_root, default_root=self._default_root)

    def _cards_dir(self, root: Path) -> Path:
        return jail_join(root, ".github/cards")

    def _spec_dir(self, root: Path, slug: str) -> Path:
        clean = spec_slug_from_reference(slug)
        if not clean:
            raise ProjectPathError("Spec slug is required")
        return jail_join(root, f"docs/specs/{clean}")

    def _find_card_path(self, root: Path, card_id: Optional[str] = None, filename: Optional[str] = None) -> Path:
        cards_dir = self._cards_dir(root)
        if filename:
            name = Path(filename).name
            return jail_join(cards_dir, name)
        cid = (card_id or "").strip()
        if not cid:
            raise FileNotFoundError("card_id or filename is required")
        if cards_dir.is_dir():
            matches = sorted(cards_dir.glob(f"{cid}-*.md")) + sorted(cards_dir.glob(f"{cid}.md"))
            # also accept case-insensitive CARD-NNN
            if not matches:
                matches = [p for p in cards_dir.glob("CARD-*.md") if extract_card_id(p.name) == cid.upper()]
            if matches:
                return matches[0]
        raise FileNotFoundError(f"Card '{cid}' not found under .github/cards")

    def _spec_exists(self, root: Path, spec_reference: str) -> bool:
        slug = spec_slug_from_reference(spec_reference)
        if not slug:
            return False
        try:
            spec_dir = self._spec_dir(root, slug)
        except ProjectPathError:
            return False
        if not spec_dir.is_dir():
            return False
        return any((spec_dir / name).is_file() for name in SPEC_FILENAMES)

    def _summarize_card(self, path: Path) -> Dict[str, Any]:
        content = path.read_text(encoding="utf-8")
        fm = parse_card_frontmatter(content)
        card_id = extract_card_id(path.name, content)
        return {
            "id": card_id,
            "title": extract_card_title(content, card_id),
            "status": fm.status,
            "spec_reference": fm.spec_reference,
            "review_rounds": fm.review_rounds,
            "max_review_rounds": fm.max_review_rounds,
            "return_reason": fm.return_reason,
            "github_issue": fm.github_issue,
            "path": str(path),
            "filename": path.name,
        }

    def list_cards(
        self,
        project_root: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        root = self._root(project_root)
        cards_dir = self._cards_dir(root)
        cards: List[Dict[str, Any]] = []
        if cards_dir.is_dir():
            for path in sorted(cards_dir.glob("CARD-*.md")):
                summary = self._summarize_card(path)
                if status and summary["status"].lower() != status.strip().lower():
                    continue
                cards.append(summary)
        return {"success": True, "project_root": str(root), "cards": cards}

    def read_card(
        self,
        card_id: Optional[str] = None,
        filename: Optional[str] = None,
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        root = self._root(project_root)
        path = self._find_card_path(root, card_id=card_id, filename=filename)
        content = path.read_text(encoding="utf-8")
        summary = self._summarize_card(path)
        summary.update({"success": True, "content": content, "project_root": str(root)})
        return summary

    def write_card(
        self,
        content: str,
        filename: Optional[str] = None,
        card_id: Optional[str] = None,
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not (content or "").strip():
            return {"success": False, "error": "content is required"}
        root = self._root(project_root)
        cards_dir = self._cards_dir(root)
        if filename:
            path = jail_join(cards_dir, Path(filename).name)
        elif card_id:
            try:
                path = self._find_card_path(root, card_id=card_id)
            except FileNotFoundError:
                slug = extract_card_title(content, card_id).lower().replace(" ", "-")
                slug = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in slug).strip("-")
                path = jail_join(cards_dir, f"{card_id}-{slug or 'card'}.md")
        else:
            cid = extract_card_id("", content)
            if not cid:
                return {"success": False, "error": "filename or card_id is required"}
            return self.write_card(content=content, card_id=cid, project_root=str(root))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        summary = self._summarize_card(path)
        summary.update({"success": True, "project_root": str(root)})
        return summary

    def set_card_status(
        self,
        card_id: str,
        status: str,
        return_reason: str = "",
        filename: Optional[str] = None,
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        root = self._root(project_root)
        path = self._find_card_path(root, card_id=card_id, filename=filename)
        content = path.read_text(encoding="utf-8")
        fm = parse_card_frontmatter(content)
        spec_exists = self._spec_exists(root, fm.spec_reference)
        ok, err = self._machine.validate(
            fm.status,
            status,
            spec_exists=spec_exists,
            review_rounds=fm.review_rounds,
            max_review_rounds=fm.max_review_rounds,
            return_reason=return_reason,
        )
        if not ok:
            return {
                "success": False,
                "error": err,
                "id": extract_card_id(path.name, content),
                "status": fm.status,
                "review_rounds": fm.review_rounds,
                "max_review_rounds": fm.max_review_rounds,
            }
        target = status
        from src.domain.sdlc.models import normalize_status

        target_n = normalize_status(target)
        if fm.status == "In Review" and target_n == "Returned":
            fm.return_reason = return_reason.strip()
            fm.review_rounds = fm.review_rounds + 1
        fm.status = target_n
        rendered = render_card_frontmatter(fm)
        path.write_text(rendered, encoding="utf-8")
        summary = self._summarize_card(path)
        summary.update({"success": True, "project_root": str(root)})
        return summary

    def read_spec(
        self,
        slug: str,
        filename: Optional[str] = None,
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        root = self._root(project_root)
        spec_dir = self._spec_dir(root, slug)
        if filename:
            path = jail_join(spec_dir, Path(filename).name)
            if not path.is_file():
                return {"success": False, "error": f"Spec file not found: {path.name}"}
            return {
                "success": True,
                "slug": spec_slug_from_reference(slug),
                "path": str(path),
                "filename": path.name,
                "content": path.read_text(encoding="utf-8"),
                "project_root": str(root),
            }
        files = []
        if spec_dir.is_dir():
            for name in SPEC_FILENAMES:
                candidate = spec_dir / name
                if candidate.is_file():
                    files.append(
                        {
                            "filename": name,
                            "path": str(candidate),
                            "content": candidate.read_text(encoding="utf-8"),
                        }
                    )
        return {
            "success": True,
            "slug": spec_slug_from_reference(slug),
            "path": str(spec_dir),
            "files": files,
            "project_root": str(root),
        }

    def write_spec(
        self,
        slug: str,
        filename: str,
        content: str,
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not filename:
            return {"success": False, "error": "filename is required"}
        root = self._root(project_root)
        spec_dir = self._spec_dir(root, slug)
        path = jail_join(spec_dir, Path(filename).name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content or "", encoding="utf-8")
        return {
            "success": True,
            "slug": spec_slug_from_reference(slug),
            "path": str(path),
            "filename": path.name,
            "project_root": str(root),
        }

    def read_steering(
        self,
        name: Optional[str] = None,
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        root = self._root(project_root)
        candidates: List[Path] = []
        if name:
            target = jail_join(root, name)
            candidates = [target]
        else:
            for rel in ("AGENTS.md", "GEMINI.md", "PROJECT.md"):
                p = root / rel
                if p.is_file():
                    candidates.append(p)
            agents_dir = root / ".agents"
            if agents_dir.is_dir():
                candidates.extend(sorted(agents_dir.rglob("*.md")))
            github_dir = root / ".github"
            if github_dir.is_dir():
                for p in sorted(github_dir.glob("*.md")):
                    candidates.append(p)
        files = []
        for path in candidates:
            if not path.is_file():
                continue
            try:
                path.relative_to(root)
            except ValueError:
                continue
            text = path.read_text(encoding="utf-8")
            headings = [ln.lstrip("#").strip() for ln in text.splitlines() if ln.startswith("#")]
            excerpt = text[:STEERING_EXCERPT_CHARS]
            files.append(
                {
                    "path": str(path),
                    "relative_path": str(path.relative_to(root)).replace("\\", "/"),
                    "headings": headings[:20],
                    "excerpt": excerpt,
                    "truncated": len(text) > STEERING_EXCERPT_CHARS,
                    "chars": len(text),
                }
            )
        return {"success": True, "project_root": str(root), "files": files}

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        registry.register_tool(
            name="list_cards",
            description="List SDLC cards under {project_root}/.github/cards. Optional status filter.",
            parameters={
                "type": "object",
                "properties": {
                    "project_root": {"type": "string", "description": "Project root. Defaults to AutoReiv checkout."},
                    "status": {"type": "string", "description": "Optional status filter (Discuss, Ready, ...)"},
                },
            },
            handler=self.list_cards,
        )
        registry.register_tool(
            name="read_card",
            description="Read one SDLC card by card_id (CARD-NNN) or filename.",
            parameters={
                "type": "object",
                "properties": {
                    "card_id": {"type": "string", "description": "Card id such as CARD-080"},
                    "filename": {"type": "string", "description": "Filename under .github/cards"},
                    "project_root": {"type": "string"},
                },
            },
            handler=self.read_card,
        )
        registry.register_tool(
            name="write_card",
            description="Write a full markdown SDLC card under .github/cards. HITL in ask mode.",
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Full markdown card including frontmatter"},
                    "filename": {"type": "string", "description": "Target filename such as CARD-080-slug.md"},
                    "card_id": {"type": "string"},
                    "project_root": {"type": "string"},
                },
                "required": ["content"],
            },
            handler=self.write_card,
        )
        registry.register_tool(
            name="set_card_status",
            description=(
                "Set card status. Enforces Discuss|Ready|In Progress|In Review|Returned|Done. "
                "Returned requires return_reason and increments review_rounds. HITL in ask mode."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "card_id": {"type": "string"},
                    "status": {"type": "string"},
                    "return_reason": {"type": "string", "description": "Required when status is Returned"},
                    "filename": {"type": "string"},
                    "project_root": {"type": "string"},
                },
                "required": ["card_id", "status"],
            },
            handler=self.set_card_status,
        )
        registry.register_tool(
            name="read_spec",
            description="Read docs/specs/<slug>/ files (requirements, design, tasks) or one filename.",
            parameters={
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                    "filename": {"type": "string"},
                    "project_root": {"type": "string"},
                },
                "required": ["slug"],
            },
            handler=self.read_spec,
        )
        registry.register_tool(
            name="write_spec",
            description="Write a spec file under docs/specs/<slug>/. HITL in ask mode.",
            parameters={
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                    "filename": {"type": "string"},
                    "content": {"type": "string"},
                    "project_root": {"type": "string"},
                },
                "required": ["slug", "filename"],
            },
            handler=self.write_spec,
        )
        registry.register_tool(
            name="read_steering",
            description="Read AGENTS.md and optional .agents / .github rules as path + excerpt, not a full dump.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Optional relative path to one steering file"},
                    "project_root": {"type": "string"},
                },
            },
            handler=self.read_steering,
        )
