"""
System Documentation & Specs Indexing Service [REQ-SKIL-004].
Safely indexes and serves repository specs, ADRs, SDLC invariants, and architecture documentation.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional


class SystemDocumentationService:
    """
    Discovers, indexes, and safely retrieves platform documentation,
    specifications, ADRs, and SDLC rules.
    """

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = (repo_root or Path(__file__).resolve().parent.parent.parent.parent).resolve()

    def get_navigation_tree(self) -> Dict[str, Any]:
        """Generate structured navigation tree for documentation browser."""
        sections: List[Dict[str, Any]] = []

        # 1. Platform Specifications
        specs_dir = self.repo_root / "docs" / "specs"
        spec_folders = []
        if specs_dir.exists():
            for spec_folder in sorted(specs_dir.iterdir(), reverse=True):
                if spec_folder.is_dir():
                    folder_name = spec_folder.name
                    folder_title = spec_folder.name.replace("-", " ").title()
                    folder_files = []
                    # Add requirements, design, tasks if exist
                    for doc_file in ["requirements.md", "design.md", "tasks.md"]:
                        fpath = spec_folder / doc_file
                        if fpath.exists():
                            rel = fpath.relative_to(self.repo_root).as_posix()
                            title = doc_file.replace(".md", "").capitalize()
                            full_title = f"{folder_title} - {title}"
                            item_obj = {"name": doc_file, "title": title, "full_title": full_title, "path": rel}
                            folder_files.append(item_obj)

                    if folder_files:
                        spec_folders.append({
                            "name": folder_name,
                            "title": folder_title,
                            "path": spec_folder.relative_to(self.repo_root).as_posix(),
                            "files": folder_files,
                        })

        if spec_folders:
            sections.append({
                "title": "Platform Specifications",
                "icon": "folder",
                "folders": spec_folders,
            })

        # 2. Architecture Decision Records (ADRs)
        adr_dir = self.repo_root / "docs" / "adr"
        adr_items = []
        if adr_dir.exists():
            for adr_file in sorted(adr_dir.glob("*.md"), reverse=True):
                if adr_file.name != "0000-template.md":
                    title = adr_file.name.replace(".md", "").replace("-", " ").title()
                    rel = adr_file.relative_to(self.repo_root).as_posix()
                    adr_items.append({"title": title, "path": rel})

        if adr_items:
            sections.append({
                "title": "Architecture Decision Records (ADRs)",
                "icon": "git-commit",
                "items": adr_items,
            })

        # 3. Master Constitution & SDLC Invariants
        sdlc_items = []
        for doc_name in [
            "AGENTS.md",
            ".agents/rules/human-engagement.md",
            ".agents/rules/sdd-ears.md",
            ".agents/rules/tdd-invariants.md",
            ".agents/rules/architecture.md",
            ".agents/rules/definition-of-done.md",
        ]:
            doc_path = self.repo_root / doc_name
            if doc_path.exists():
                title = doc_name.split("/")[-1].replace(".md", "").replace("-", " ").title()
                rel = doc_path.relative_to(self.repo_root).as_posix()
                sdlc_items.append({"title": title, "path": rel})

        if sdlc_items:
            sections.append({
                "title": "SDLC Constitution & Invariants",
                "icon": "shield-alert",
                "items": sdlc_items,
            })

        # 4. Requirements Traceability Matrix (RTM)
        rtm_file = self.repo_root / "docs" / "rtm.json"
        if rtm_file.exists():
            sections.append({
                "title": "Traceability & RTM",
                "icon": "check-circle",
                "items": [{"title": "Requirements Traceability Matrix (RTM)", "path": "docs/rtm.json"}],
            })

        return {"sections": sections}

    def get_doc_content(self, rel_path: str) -> Dict[str, Any]:
        """
        Safely retrieve file content with strict path traversal prevention.
        """
        clean_rel = rel_path.strip().lstrip("/\\")

        # Resolve path
        target_path = (self.repo_root / clean_rel).resolve()

        # Strict security constraint: must be inside repo_root
        if not str(target_path).startswith(str(self.repo_root)):
            raise ValueError(f"Access denied: path '{rel_path}' is outside repository root.")

        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError(f"Documentation file '{rel_path}' not found.")

        # Whitelist allowed extensions
        if target_path.suffix.lower() not in [".md", ".json", ".txt", ".yaml", ".yml"]:
            raise ValueError(f"Unsupported documentation file format: '{target_path.suffix}'")

        content = target_path.read_text(encoding="utf-8")
        title = target_path.name.replace(".md", "").replace(".json", "").replace("-", " ").title()

        fmt = "json" if target_path.suffix.lower() == ".json" else "markdown"

        return {
            "path": target_path.relative_to(self.repo_root).as_posix(),
            "title": title,
            "format": fmt,
            "content": content,
        }
