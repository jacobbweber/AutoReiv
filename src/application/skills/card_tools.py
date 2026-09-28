"""
Card, spec, and steering tools for the spec-driven SDLC loop [REQ-SDLC-010..014].
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.sdlc.paths import ProjectPathError, jail_join, resolve_project_root
from src.domain.sdlc.models import (
    CardStatusMachine,
    extract_card_id,
    extract_card_title,
    parse_card_frontmatter,
    serialize_card_frontmatter,
    spec_slug_from_reference,
)

STEERING_EXCERPT_CHARS = 4000
SPEC_FILENAMES = ("requirements.md", "design.md", "tasks.md")
# CARD-562 D2: the status moves Developer may make itself.
DEVELOPER_TRANSITIONS = frozenset(
    {("Ready", "In Progress"), ("In Progress", "In Review"), ("Returned", "In Progress")}
)
# CARD-563: Architect plans cards; review (Done / Returned) is slice 3.
ARCHITECT_TRANSITIONS = frozenset({("Discuss", "Ready"), ("Proposed", "Ready"), ("Ready", "Proposed")})
ARCHITECT_NEW_STATUSES = ("Proposed", "Ready")
ARCHITECT_LOCKED_STATUSES = ("In Progress", "In Review")
# CARD-562: preferred card folder first; the other two are fallbacks for older projects.
CARD_DIRS = (".agents/cards", "docs/cards", ".github/cards")
_CARD_NUM = re.compile(r"^CARD-(\d+)", re.IGNORECASE)


def cards_folder_refusal(root: Path, target: Path) -> str:
    """CARD-562: generic file tools never write cards; write_card owns ids, filenames and status rules."""
    try:
        rel = Path(target).resolve().relative_to(Path(root).resolve()).as_posix()
    except (OSError, ValueError):
        return ""
    for d in CARD_DIRS:
        if rel == d or rel.startswith(d + "/"):
            return (
                f"Refusing to write '{rel}' with a file tool: cards are written with write_card (new cards get the "
                "next CARD-N id and filename automatically) and moved with set_card_status. Reading cards is fine."
            )
    return ""


def _slug(title: str) -> str:
    title = re.sub(r"^\s*\[?[A-Z]+(?:-[A-Z]+)*-(?:\d+|<n>|n)\]?:?\s*", "", title or "", flags=re.IGNORECASE)
    slug = "".join(ch if ch.isalnum() else "-" for ch in title.lower())
    return re.sub(r"-+", "-", slug).strip("-")[:60].strip("-") or "card"


EVIDENCE_AUTO_HEADER = "Recorded by set_card_status (In Review):"


def insert_evidence(card: str, lines: List[str]) -> str:
    """Put the tool's evidence first in ## Evidence (or ## Results), keeping what the model already wrote below it."""
    block = EVIDENCE_AUTO_HEADER + "\n" + "\n".join(lines) + "\n"
    text = card if card.endswith("\n") else card + "\n"
    m = re.search(r"(?m)^##\s+(Evidence|Results)\s*$", text)
    if not m:
        return text + "\n## Evidence\n\n" + block
    nxt = re.search(r"(?m)^##\s+", text[m.end():])
    end = m.end() + nxt.start() if nxt else len(text)
    existing = text[m.end():end].strip("\n")
    body = "\n\n" + block + (("\n" + existing + "\n") if existing.strip() else "")
    return text[: m.end()] + body + ("\n" if nxt else "") + text[end:]


def apply_card_title(content: str, title: str, new: bool) -> str:
    """CARD-562: a `title` argument sets the frontmatter title and the heading text (and so the new card's slug)."""
    text = content.replace("\r\n", "\n")
    safe = title.replace('"', "'")
    if text.lstrip().startswith("---"):
        start = text.index("---")
        end = text.find("\n---", start + 3)
        if end != -1:
            head, rest = text[:end], text[end:]
            if re.search(r"(?m)^title:", head):
                head = re.sub(r"(?m)^title:.*$", lambda _m: f'title: "{safe}"', head, count=1)
            else:
                head = head + f'\ntitle: "{safe}"'
            text = head + rest
    m = re.search(r"(?m)^#\s+(\[?[A-Z]+(?:-[A-Z]+)*-\d+\]?\s*)?.*$", text)
    if m:
        ident = (m.group(1) or "").strip()
        heading = f"# {ident + ' ' if ident else ''}{title}"
        text = text[: m.start()] + heading + text[m.end():]
    elif new:
        text = re.sub(r"(?s)^(---.*?\n---\n)?", lambda mm: (mm.group(0) or "") + f"\n# {title}\n", text, count=1)
    return text


def stamp_new_card(content: str, card_id: str, status: Optional[str] = None) -> str:
    """Set the frontmatter id (and optionally status) and the heading id of a new card."""
    text = content.replace("\r\n", "\n")
    if not text.lstrip().startswith("---"):
        if status:  # a status is forced (Developer): give the card YAML frontmatter
            text = f"---\nid: {card_id}\nstatus: {status}\n---\n" + text
    else:
        start = text.index("---")
        end = text.find("\n---", start + 3)
        if end == -1:
            end = len(text)
        head, rest = text[:end], text[end:]
        head = re.sub(r"(?m)^id:.*$", f"id: {card_id}", head, count=1) if re.search(r"(?m)^id:", head) else (
            head[: start + 3] + f"\nid: {card_id}" + head[start + 3 :]
        )
        if status:
            head = re.sub(r"(?m)^status:.*$", f"status: {status}", head, count=1) if re.search(r"(?m)^status:", head) else (
                head + f"\nstatus: {status}"
            )
        text = head + rest
    return re.sub(
        r"(?m)^(#\s+)(?:\[?[A-Z]+(?:-[A-Z]+)*-(?:\d+|<n>|N)\]?:?\s*)?",  # CARD-563: also the CARD-<n> placeholder
        lambda m: f"{m.group(1)}{card_id} ",
        text,
        count=1,
    )


class CardTools:
    """Markdown cards + specs under a project_root. No second workflow engine."""

    def __init__(
        self,
        default_project_root: Optional[str] = None,
        root_resolver: Optional[Callable[[Optional[str]], Path]] = None,
        check_record: Any = None,
    ):
        from src.application.sdlc.check_record import default_record

        self._default_root = Path(default_project_root).resolve() if default_project_root else None
        self._root_resolver = root_resolver
        self._machine = CardStatusMachine()
        self._check_record = check_record or default_record()

    def _root(self, project_root: Optional[str] = None) -> Path:
        if self._root_resolver is not None:
            return Path(self._root_resolver(project_root)).resolve()
        return resolve_project_root(project_root, default_root=self._default_root)

    def _cards_dir(self, root: Path) -> Path:
        # CARD-562: cards live in .agents/cards/. An older project that only has docs/cards or .github/cards
        # keeps using that folder; a project with none gets .agents/cards.
        for rel in CARD_DIRS:
            if (root / rel).is_dir():
                return jail_join(root, rel)
        return jail_join(root, CARD_DIRS[0])

    def _all_cards_dirs(self, root: Path) -> List[Path]:
        dirs: List[Path] = []
        for rel in CARD_DIRS:
            p = root / Path(rel)
            if p.is_dir():
                dirs.append(p)
        return dirs or [jail_join(root, CARD_DIRS[0])]

    def _spec_dir(self, root: Path, slug: str) -> Path:
        clean = spec_slug_from_reference(slug)
        if not clean:
            raise ProjectPathError("Spec slug is required")
        agents_specs = root / ".agents" / "specs"
        if (agents_specs / clean).is_dir():
            return jail_join(root, f".agents/specs/{clean}")
        docs_specs = root / "docs" / "specs"
        if (docs_specs / clean).is_dir():
            return jail_join(root, f"docs/specs/{clean}")
        if agents_specs.is_dir() or not docs_specs.is_dir():
            return jail_join(root, f".agents/specs/{clean}")
        return jail_join(root, f"docs/specs/{clean}")

    def _find_card_path(self, root: Path, card_id: Optional[str] = None, filename: Optional[str] = None) -> Path:
        cards_dirs = self._all_cards_dirs(root)
        if filename:
            name = Path(filename).name
            for cdir in cards_dirs:
                candidate = jail_join(cdir, name)
                if candidate.is_file():
                    return candidate
            return jail_join(self._cards_dir(root), name)
        cid = (card_id or "").strip()
        if not cid:
            raise FileNotFoundError("card_id or filename is required")
        for cdir in cards_dirs:
            if cdir.is_dir():
                matches = sorted(cdir.glob(f"{cid}-*.md")) + sorted(cdir.glob(f"{cid}.md"))
                if not matches:
                    matches = [p for p in cdir.glob("CARD-*.md") if extract_card_id(p.name) == cid.upper()]
                if matches:
                    return matches[0]
        raise FileNotFoundError(f"Card '{cid}' not found under " + ", ".join(CARD_DIRS))

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
        cards_dirs = self._all_cards_dirs(root)
        cards: List[Dict[str, Any]] = []
        seen_ids = set()
        for cards_dir in cards_dirs:
            if cards_dir.is_dir():
                for path in sorted(cards_dir.glob("CARD-*.md")):
                    summary = self._summarize_card(path)
                    cid = summary.get("id")
                    if cid and cid in seen_ids:
                        continue
                    if cid:
                        seen_ids.add(cid)
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

    def _next_card_id(self, root: Path) -> str:
        top = 0
        for cdir in self._all_cards_dirs(root):
            if cdir.is_dir():
                for p in cdir.glob("CARD-*.md"):
                    m = _CARD_NUM.match(p.name)
                    if m:
                        top = max(top, int(m.group(1)))
        return f"CARD-{top + 1}"

    def _existing_card(self, root: Path, filename: Optional[str], card_id: Optional[str], content: str) -> Optional[Path]:
        if filename:
            for cdir in self._all_cards_dirs(root):
                cand = jail_join(cdir, Path(filename).name)
                if cand.is_file():
                    return cand
        for cid in (card_id, extract_card_id(Path(filename).name if filename else "", "") if filename else "",
                    extract_card_id("", content)):
            if cid:
                try:
                    return self._find_card_path(root, card_id=cid)
                except FileNotFoundError:
                    continue
        return None

    def write_card(
        self,
        content: str,
        filename: Optional[str] = None,
        card_id: Optional[str] = None,
        project_root: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not (content or "").strip():
            return {"success": False, "error": "content is required"}
        root = self._root(project_root)
        cards_dir = self._cards_dir(root)
        path = self._existing_card(root, filename, card_id, content)
        if title and title.strip():
            content = apply_card_title(content, title.strip(), new=path is None)
        assigned = ""
        if path is None:
            # CARD-562: new cards get the next CARD-N id and a CARD-N-slug.md filename; Developer's are Proposed.
            developer = self._actor() == "developer"
            wanted = (card_id or extract_card_id(Path(filename).name if filename else "", content) or "").upper()
            assigned = wanted if (wanted and not developer) else self._next_card_id(root)
            forced = "Proposed" if developer else self._architect_new_status(content)
            if forced or extract_card_id("", content) != assigned:
                content = stamp_new_card(content, assigned, forced or None)
            keep_name = filename and not developer and extract_card_id(Path(filename).name) == assigned
            name = Path(filename).name if keep_name else f"{assigned}-{_slug(extract_card_title(content, assigned))}.md"
            path = jail_join(cards_dir, name)
        refused = self._developer_write_refusal(path, content) or self._architect_write_refusal(path, content)
        if refused:
            return {"success": False, "error": refused}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        summary = self._summarize_card(path)
        summary.update({"success": True, "project_root": str(root)})
        if assigned:
            summary["assigned_id"] = assigned
        return summary

    @staticmethod
    def _actor() -> str:
        from src.application.kernel.tool_registry import get_tool_context

        return str(get_tool_context().get("agent_id") or "").lower()

    def _architect_new_status(self, content: str) -> str:
        """CARD-563: a new Architect card is Proposed or Ready; no status means Proposed."""
        if self._actor() != "architect":
            return ""
        from src.domain.sdlc.models import normalize_status

        explicit = re.search(r"(?im)^\s*(?:status\s*:|>\s*\*\*status\*\*)", content)
        status = normalize_status(parse_card_frontmatter(content).status or "") if explicit else ""
        return status if status in ARCHITECT_NEW_STATUSES else ("Proposed" if not status else "")

    def _architect_write_refusal(self, path: Path, content: str) -> str:
        """CARD-563: Architect writes Proposed/Ready cards and leaves cards Developer is working or that wait for review."""
        if self._actor() != "architect":
            return ""
        from src.domain.sdlc.models import normalize_status

        new_status = normalize_status(parse_card_frontmatter(content).status or "")
        if not path.is_file():
            if new_status not in ARCHITECT_NEW_STATUSES:
                return "Architect files new cards with status: Proposed or Ready."
            return ""
        old_status = normalize_status(parse_card_frontmatter(path.read_text(encoding="utf-8")).status or "")
        if old_status in ARCHITECT_LOCKED_STATUSES:
            return (
                f"This card is {old_status}: Developer is working it or it waits for review, so Architect does not edit it. "
                "File a new card for further changes."
            )
        if new_status != old_status:
            return f"Keep status: {old_status} when editing a card; change status with set_card_status."
        return ""

    def _developer_write_refusal(self, path: Path, content: str) -> str:
        """CARD-562 D2: Developer files new cards as Proposed and never changes a status by rewriting a card."""
        if self._actor() != "developer":
            return ""
        from src.domain.sdlc.models import normalize_status

        new_status = normalize_status(parse_card_frontmatter(content).status or "")
        if not path.is_file():
            if new_status != "Proposed":
                return "Developer files new cards with status: Proposed. Jacob or Architect makes them Ready."
            return ""
        old_status = normalize_status(parse_card_frontmatter(path.read_text(encoding="utf-8")).status or "")
        if new_status != old_status:
            return f"Keep status: {old_status} when editing a card; change status with set_card_status."
        return ""

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
        from src.application.kernel.tool_registry import get_tool_context
        from src.domain.sdlc.models import normalize_status

        target_n = normalize_status(status)
        actor = str(get_tool_context().get("agent_id") or "").lower()
        passed_through = ""
        if actor == "developer" and target_n == "In Review" and normalize_status(fm.status) == "Ready":
            fm.status = "In Progress"  # CARD-562: Ready -> In Review goes through In Progress in one call
            passed_through = "Ready -> In Progress -> In Review"
        if actor == "developer" and (normalize_status(fm.status), target_n) not in DEVELOPER_TRANSITIONS:
            return {
                "success": False,
                "error": "Developer may move a card Ready -> In Progress, In Progress -> In Review, or Returned -> "
                "In Progress. Ready, Done and Returned are set by Jacob or Architect.",
                "id": extract_card_id(path.name, content),
                "status": fm.status,
            }
        if actor == "architect" and (normalize_status(fm.status) or "Discuss", target_n) not in ARCHITECT_TRANSITIONS:
            review = target_n in ("Done", "Returned")
            return {
                "success": False,
                "error": (
                    f"Architect does not set {target_n}: review is slice 3 (CARD-564). Jacob reviews In Review cards."
                    if review
                    else "Architect may move a card Discuss/Proposed -> Ready or Ready -> Proposed only; "
                    "Developer moves it on from Ready (use hand_off_card)."
                ),
                "id": extract_card_id(path.name, content),
                "status": fm.status,
            }
        if actor == "coding":
            if not (fm.status == "In Progress" and target_n == "In Review"):
                return {
                    "success": False,
                    "error": "Coding may set_card_status In Progress -> In Review only.",
                    "id": extract_card_id(path.name, content),
                    "status": fm.status,
                }

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
        gated = actor == "developer" and target_n == "In Review"
        if gated:
            refusal = self._in_review_refusal(root, path)
            if refusal:
                return {"success": False, "error": refusal, "id": extract_card_id(path.name, content), "status": fm.status}
        if fm.status == "In Review" and target_n == "Returned":
            fm.return_reason = return_reason.strip()
            fm.review_rounds = fm.review_rounds + 1
        fm.status = target_n
        rendered = serialize_card_frontmatter(fm)
        if gated:
            rendered = insert_evidence(rendered, self._evidence_lines(root))
        path.write_text(rendered, encoding="utf-8")
        committed: Dict[str, Any] = {}
        if gated:
            committed = self._commit_card(root, path, extract_card_id(path.name, content))
            if not committed.get("success", True):
                path.write_text(content, encoding="utf-8")  # leave the card as it was
                return {"success": False, "error": committed["error"], "id": extract_card_id(path.name, content), "status": fm.status}
        summary = self._summarize_card(path)
        summary.update({"success": True, "project_root": str(root)})
        summary.update({k: v for k, v in committed.items() if k != "success"})
        if passed_through:
            summary["transition"] = passed_through
        return summary

    def _evidence_lines(self, root: Path) -> List[str]:
        """Tool-written evidence: branch, commits since base, files changed, recorded green checks [CARD-562]."""
        from src.application.sdlc.check_record import NO_GIT_HEAD, git_branch, git_head, run_git
        from src.domain.sdlc.agents_contract import parse_agents_md

        agents = root / "AGENTS.md"
        contract = parse_agents_md(agents.read_text(encoding="utf-8", errors="replace") if agents.is_file() else "")
        head = git_head(root)
        lines: List[str] = []
        if head != NO_GIT_HEAD:
            base = contract.base_branch or "main"
            lines.append(f"- Branch: `{git_branch(root)}` (base `{base}`)")
            log = run_git(root, ["log", "--format=%h %s", f"{base}..HEAD"])
            commits = [c for c in log.stdout.splitlines() if c.strip()] if log.returncode == 0 else []
            lines.append("- Commits since base: " + ("; ".join(f"`{c}`" for c in commits) if commits else "none"))
            diff = run_git(root, ["diff", "--name-only", f"{base}...HEAD"])
            changed = [f for f in diff.stdout.splitlines() if f.strip()] if diff.returncode == 0 else []
            lines.append("- Files changed: " + (", ".join(f"`{f}`" for f in changed) if changed else "none"))
        rec = self._check_record.get(root) or {}
        cmds = rec.get("commands") or {}
        checks = ", ".join(f"{n} (`{cmds.get(n) or contract.checks.get(n, '?')}`)" for n in rec.get("checks") or [])
        where = f"HEAD `{str(rec.get('head', ''))[:12]}`" if head != NO_GIT_HEAD else "this project"
        lines.append(f"- Green run_project_checks for {where} at {rec.get('at', '?')}: {checks or 'none'} - passed")
        return lines

    def _in_review_refusal(self, root: Path, path: Path) -> str:
        """CARD-562: Developer's In Review is enforced here: card branch, clean tree, green checks for HEAD."""
        from src.application.sdlc.check_record import NO_GIT_HEAD, git_branch, git_dirty_paths, git_head
        from src.application.skills.git_tools import PROTECTED_COMMIT_BRANCHES

        head = git_head(root)
        if head != NO_GIT_HEAD:
            branch = git_branch(root)
            if branch in PROTECTED_COMMIT_BRANCHES or branch in ("", "HEAD"):
                return (
                    f"Not In Review from '{branch or 'a detached HEAD'}'. Create the card branch with git_create_branch, "
                    "commit the work there with git_commit, run run_project_checks, then set In Review again."
                )
            card_rel = path.resolve().relative_to(root.resolve()).as_posix()
            others = [p for p in git_dirty_paths(root) if p != card_rel]
            if others:
                return (
                    "Not In Review: uncommitted changes besides this card: " + ", ".join(others[:8])
                    + ". Commit them with git_commit (paths=[...]), run run_project_checks until passed, "
                    "then set In Review again. The card file itself is committed for you."
                )
        rec = self._check_record.get(root)
        if not rec or rec.get("head") != head:
            where = f"HEAD {head[:12]}" if head != NO_GIT_HEAD else "this project"
            return (
                f"Not In Review: no green run_project_checks recorded for {where}. Run run_project_checks now "
                "(with all code committed); when it returns passed=true, set In Review again."
            )
        return ""

    def _commit_card(self, root: Path, path: Path, card_id: str) -> Dict[str, Any]:
        """Commit only the card file with a conventional message; return the commit id for the evidence."""
        from src.application.sdlc.check_record import NO_GIT_HEAD, git_head, run_git

        if git_head(root) == NO_GIT_HEAD:
            return {"success": True, "commit": None, "note": "Not a git repository: nothing committed."}
        rel = path.resolve().relative_to(root.resolve()).as_posix()
        message = f"docs(card): {card_id or path.stem} In Review"
        added = run_git(root, ["add", "--", rel])
        if added.returncode != 0:
            return {"success": False, "error": f"git add failed for {rel}: {added.stderr.strip()}"}
        done = run_git(root, ["commit", "-m", message, "--", rel])
        if done.returncode != 0:
            return {"success": False, "error": f"Committing the card failed: {(done.stderr or done.stdout).strip()}"}
        return {"success": True, "commit": git_head(root)[:12], "commit_message": message}

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

    def _steering_dir(self, root: Path) -> Path:
        agents_steering = root / ".agents" / "steering"
        if agents_steering.is_dir():
            return jail_join(root, ".agents/steering")
        root_steering = root / "steering"
        if root_steering.is_dir():
            return jail_join(root, "steering")
        return jail_join(root, ".agents/steering")

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
            for rel in ("AGENTS.md", "GEMINI.md", "PROJECT.md", ".agents/agents.md"):
                p = root / rel
                if p.is_file() and p not in candidates:
                    candidates.append(p)
            steering_dir = self._steering_dir(root)
            if steering_dir.is_dir():
                for p in sorted(steering_dir.glob("*.md")):
                    if p not in candidates:
                        candidates.append(p)
            root_steering = root / "steering"
            if root_steering.is_dir() and root_steering != steering_dir:
                for p in sorted(root_steering.glob("*.md")):
                    if p not in candidates:
                        candidates.append(p)
            agents_dir = root / ".agents"
            if agents_dir.is_dir():
                for p in sorted(agents_dir.glob("*.md")):
                    if p not in candidates:
                        candidates.append(p)
            github_dir = root / ".github"
            if github_dir.is_dir():
                for p in sorted(github_dir.glob("*.md")):
                    if p not in candidates:
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
            description="List SDLC cards under {project_root}/.agents/cards. Optional status filter.",
            parameters={
                "type": "object",
                "properties": {
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
                    "filename": {"type": "string", "description": "Filename under .agents/cards"},
                },
            },
            handler=self.read_card,
        )
        registry.register_tool(
            name="write_card",
            description=(
                "Write a full markdown SDLC card under .agents/cards (the only way to create or edit a card). "
                "A new card gets the next CARD-N id and filename automatically; Developer's new cards are Proposed. "
                "HITL in ask mode."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Full markdown card including frontmatter"},
                    "filename": {"type": "string", "description": "Target filename such as CARD-080-slug.md"},
                    "card_id": {"type": "string"},
                    "title": {"type": "string", "description": "Card title; sets the heading and the new card's filename slug"},
                },
                "required": ["content"],
            },
            handler=self.write_card,
        )
        registry.register_tool(
            name="set_card_status",
            description=(
                "Set card status. Enforces Discuss|Ready|In Progress|In Review|Returned|Done. "
                "Returned requires return_reason and increments review_rounds. HITL in ask mode. "
                "Developer In Review needs the card branch, all code committed and a green run_project_checks for "
                "HEAD; the tool then commits the card file and returns the commit id."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "card_id": {"type": "string"},
                    "status": {"type": "string"},
                    "return_reason": {"type": "string", "description": "Required when status is Returned"},
                    "filename": {"type": "string"},
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
                },
            },
            handler=self.read_steering,
        )
