"""HTML template loader with partial-include expansion for src/web/templates/index.html."""
from __future__ import annotations

import re
from pathlib import Path

_INCLUDE_RE = re.compile(r"^[ \t]*<!--\s*@include\s+([a-zA-Z0-9_./-]+)\s*-->[ \t]*$", re.MULTILINE)


def expand_html_includes(html_text: str, base_dir: Path) -> str:
    """Expand `<!-- @include partials/foo.html -->` directives relative to `base_dir`."""
    if "<!-- @include " not in html_text:
        return html_text

    def _replace(match: re.Match[str]) -> str:
        rel_path = match.group(1)
        target = (base_dir / rel_path).resolve()
        if not target.is_relative_to(base_dir.resolve()):
            raise ValueError(f"Include path escapes template directory: {rel_path}")
        if not target.is_file():
            raise FileNotFoundError(f"Missing HTML partial: {target}")
        text = target.read_text(encoding="utf-8")
        return text[:-1] if text.endswith("\n") else text

    return _INCLUDE_RE.sub(_replace, html_text)


def load_index_html(template_dir: Path) -> str:
    """Load `index.html` from `template_dir` and expand any `@include` partials."""
    index_file = template_dir / "index.html"
    raw = index_file.read_text(encoding="utf-8")
    return expand_html_includes(raw, template_dir)
