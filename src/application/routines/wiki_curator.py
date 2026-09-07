"""
Autonomous Wiki Curation Routine [CARD-173].
Inspects 00_Inbox/, validates frontmatter, checks and self-registers tag authority,
deduplicates against 01_Notes/, scrubs conversational fluff, and graduates notes to the warehouse.
"""

from __future__ import annotations

import datetime as dt
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.domain.wiki.frontmatter import (
    FrontmatterParser,
    WikiNoteMeta,
    clean_note_content,
    compute_content_hash,
    compute_context_tokens,
    compute_word_count,
)
from src.domain.wiki.store import WikiStore, slugify

log = logging.getLogger(__name__)

_TAG_LINE_RE = re.compile(r"^-\s+`?([a-zA-Z0-9_-]+)`?", re.MULTILINE)


class WikiCuratorRoutine:
    """
    Autonomous routine that manages the lifecycle of staged notes in 00_Inbox/,
    curating them into the permanent 01_Notes/ warehouse.
    """

    def __init__(self, store: Optional[WikiStore] = None):
        self.store = store or WikiStore()
        self.store.scaffold()

    def _get_tag_authority_path(self) -> Path:
        tag_auth = self.store.root_dir / "02_Resources" / "_Templates" / "tag-authority.md"
        if not tag_auth.exists():
            self.store.scaffold()
        return tag_auth

    def _load_registered_tags(self) -> Set[str]:
        auth_file = self._get_tag_authority_path()
        if not auth_file.exists():
            return set()
        text = auth_file.read_text(encoding="utf-8", errors="replace")
        matches = _TAG_LINE_RE.findall(text)
        return {m.lower().strip() for m in matches}

    def _register_tag_if_novel(self, domain: str, tag: str) -> None:
        auth_file = self._get_tag_authority_path()
        clean_tag = tag.strip().lower()
        registered = self._load_registered_tags()

        # Direct or punctuation-invariant match
        clean_key = clean_tag.replace("-", "").replace("_", "")
        for reg in registered:
            if reg.replace("-", "").replace("_", "") == clean_key:
                return

        # Tag is genuinely novel: append and self-register
        text = auth_file.read_text(encoding="utf-8", errors="replace") if auth_file.exists() else "# Wiki Tag Authority\n\n"
        safe_domain = slugify(domain) or "general"
        domain_heading = f"### {safe_domain}"

        if domain_heading in text:
            # Append under the existing domain section
            parts = text.split(domain_heading, 1)
            updated_text = f"{parts[0]}{domain_heading}\n- `{clean_tag}`{parts[1]}"
        else:
            # Append a new domain section
            updated_text = f"{text.rstrip()}\n\n{domain_heading}\n- `{clean_tag}`\n"

        auth_file.write_text(updated_text, encoding="utf-8")
        log.info(f"Self-registered novel tag '{clean_tag}' under domain '{safe_domain}' in tag-authority.md")

    def curate_inbox(self) -> Dict[str, Any]:
        """
        Execute full curation pass across all notes currently in 00_Inbox/.
        """
        inbox_dir = self.store.root_dir / "00_Inbox"
        if not inbox_dir.exists():
            return {"success": True, "curated_count": 0, "actions": ["Inbox directory does not exist."]}

        inbox_files = sorted(list(inbox_dir.glob("*.md")))
        if not inbox_files:
            return {"success": True, "curated_count": 0, "actions": ["Inbox is empty. Zero notes to curate."]}

        actions: List[str] = []

        for f in inbox_files:
            raw_text = f.read_text(encoding="utf-8", errors="replace")
            meta, body = FrontmatterParser.parse(raw_text)

            title = meta.title or f.stem.replace("_", " ").title()
            domain = slugify(meta.domain) or "general"
            topic = slugify(meta.topic) or "general"
            tags = list(meta.tags or [])

            # 1. Scrub conversational AI preambles and sign-offs
            cleaned_body = clean_note_content(body)

            # 2. Check and self-register tags with tag authority
            for t in tags:
                self._register_tag_if_novel(domain, t)

            # 3. Deduplication: Check if permanent note already exists in 01_Notes/
            slug = slugify(title)
            expected_permanent_rel = f"01_Notes/{domain}/{topic}/{slug}.md"
            expected_permanent_file = self.store.root_dir / expected_permanent_rel

            # Also check if any existing notes match title exactly
            existing_match_path: Optional[str] = None
            if expected_permanent_file.exists():
                existing_match_path = expected_permanent_rel
            else:
                for candidate in self.store.list_notes():
                    if candidate["path"].startswith("01_Notes/"):
                        if candidate["title"].strip().lower() == title.strip().lower() or candidate["path"].endswith(f"/{slug}.md"):
                            existing_match_path = candidate["path"]
                            break

            if existing_match_path:
                # Merge / Append into existing note
                today_str = dt.date.today().isoformat()
                self.store.append_note(
                    relative_path=existing_match_path,
                    content=cleaned_body,
                    heading=f"Update: {title} ({today_str})",
                )
                f.unlink(missing_ok=True)
                actions.append(f"Merged inbox note '{title}' into existing note '{existing_match_path}'.")
            else:
                # Graduate note to permanent warehouse
                target_file = self.store.root_dir / expected_permanent_rel
                target_file.parent.mkdir(parents=True, exist_ok=True)

                words = compute_word_count(cleaned_body)
                tokens = compute_context_tokens(cleaned_body)
                content_hash = compute_content_hash(cleaned_body)
                today = dt.date.today().isoformat()

                grad_meta_dict = {
                    "uid": meta.uid,
                    "title": title,
                    "domain": domain,
                    "topic": topic,
                    "category": "notes",
                    "document_type": meta.document_type if meta.document_type != "note" else "atomic_note",
                    "tags": tags,
                    "summary": meta.summary,
                    "status": "final",
                    "priority": getattr(meta, "priority", "medium"),
                    "sensitivity": getattr(meta, "sensitivity", "internal"),
                    "pinned": getattr(meta, "pinned", False),
                    "author": meta.author or "assistant",
                    "date_created": getattr(meta, "date_created", today),
                    "last_updated": today,
                    "last_accessed": today,
                    "word_count": words,
                    "context_tokens": tokens,
                    "content_hash": content_hash,
                    "schema_version": "1.0",
                }
                grad_meta = WikiNoteMeta(**grad_meta_dict)
                full_serialized = FrontmatterParser.dump(grad_meta, cleaned_body)
                target_file.write_text(full_serialized, encoding="utf-8")

                f.unlink(missing_ok=True)
                actions.append(f"Graduated inbox note '{title}' to '{expected_permanent_rel}'.")

        return {
            "success": True,
            "curated_count": len(actions),
            "actions": actions,
        }
