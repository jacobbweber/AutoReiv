"""CARD-440: Wiki curation from links / curriculum (Tutor Learning OS path).

REQ-440-001..004: durable wiki_note_create path from Tutor education mode;
catalogued education templates; raw sources MAY omit education tags;
failures do not claim library updated; Education Studio wiki chrome stays.
"""

from __future__ import annotations

from pathlib import Path

from src.application.education.wiki_curation import (
    HTTP_CONTRACT,
    SKILL_ID,
    catalog_education_templates,
    curate_from_curriculum,
    curate_from_link,
    fetch_link_text,
    parse_curriculum_bullets,
)
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.education_tools import EducationTools
from src.application.skills.wiki_tools import WikiTools


CURATION_TOOL_NAMES = (
    "education_wiki_template_catalog",
    "education_wiki_curate_from_link",
    "education_wiki_curate_from_curriculum",
)


def _wiki(tmp_path: Path) -> WikiTools:
    root = tmp_path / "wiki"
    root.mkdir(parents=True, exist_ok=True)
    # Minimal scaffold dirs wiki_note_create expects
    (root / "00_Inbox").mkdir(exist_ok=True)
    (root / "01_Notes").mkdir(exist_ok=True)
    (root / "02_Resources" / "_Templates").mkdir(parents=True, exist_ok=True)
    return WikiTools(wiki_root=root)


def test_curation_tools_register_on_registry():
    registry = ScopedToolRegistry()
    EducationTools().register_tools(registry)
    for name in CURATION_TOOL_NAMES:
        assert name in registry._tools
        assert registry.get_tool_origin(name) == "platform"


def test_template_catalog_lists_education_templates():
    """[REQ-440-002] Catalogued education templates are discoverable."""
    items = catalog_education_templates()
    slugs = {i["slug"] for i in items}
    assert "education-concept" in slugs
    assert "education-priming" in slugs
    assert "education-quiz" in slugs
    tools = EducationTools()
    catalog = tools.education_wiki_template_catalog()
    assert catalog.get("success") is True
    assert catalog.get("skill_hint") == SKILL_ID
    assert catalog.get("count") >= 8


def test_curate_from_link_writes_durable_note_readable(tmp_path: Path):
    """[REQ-440-001] Link curation writes a note path wiki_note_read returns."""
    wiki = _wiki(tmp_path)
    body = "Bayes theorem relates prior, likelihood, and posterior."
    result = curate_from_link(
        wiki,
        url="https://example.com/bayes",
        topic="Bayes",
        title="Bayes Overview",
        template="education-concept",
        body=body,
    )
    assert result.get("success") is True
    assert result.get("durable") is True
    assert result.get("skill_hint") == SKILL_ID
    assert result.get("http_contract") == HTTP_CONTRACT
    path = result.get("path") or ""
    assert path
    assert path.replace("\\", "/").startswith("00_Inbox/")
    assert result.get("education_tags") is True
    assert result.get("template") == "education-concept"

    read = wiki.read_wiki_note(relative_path=path)
    assert read.get("success") is True or "content" in read or "path" in read
    content = str(read.get("content") or read.get("body") or "")
    if not content and hasattr(wiki.store, "read_note"):
        content = str(wiki.store.read_note(path).get("content") or "")
    assert "Bayes" in content or "prior" in content.lower() or body.split()[0] in content

    # Agent tool wrapper
    tools = EducationTools(wiki_root=tmp_path / "wiki")
    via_tool = tools.education_wiki_curate_from_link(
        url="https://example.com/bayes-2",
        topic="Bayes",
        title="Bayes Tool Path",
        template="education-concept",
        body=body,
    )
    assert via_tool.get("success") is True
    assert via_tool.get("durable") is True
    tool_path = via_tool.get("path") or ""
    assert tool_path
    read2 = wiki.read_wiki_note(relative_path=tool_path)
    assert read2.get("success") is not False


def test_raw_source_link_omits_education_tags(tmp_path: Path):
    """[REQ-440-002] Raw sources MAY omit education tags."""
    wiki = _wiki(tmp_path)
    result = curate_from_link(
        wiki,
        url="https://example.com/raw-paper",
        topic="Papers",
        title="Raw Paper Dump",
        raw_source=True,
        body="Unstructured source text about kernels.",
    )
    assert result.get("success") is True
    assert result.get("raw_source") is True
    assert result.get("education_tags") is False
    path = result.get("path") or ""
    assert path
    note = wiki.store.read_note(path)
    content = str(note.get("content") or "")
    fm = str(note.get("frontmatter") or note.get("meta") or "")
    blob = content + "\n" + fm + "\n" + str(note)
    # Must not force education tag on raw sources
    tags = note.get("frontmatter", {}).get("tags") if isinstance(note.get("frontmatter"), dict) else None
    if tags is None:
        # parse from content frontmatter
        assert "education" not in content.split("---", 2)[1].lower() or "tags: [\"source\"" in content or "source" in content
    else:
        assert "education" not in [str(t).lower() for t in tags]


def test_curate_from_curriculum_writes_templated_notes(tmp_path: Path):
    """[REQ-440-001/002] Curriculum bullets become durable templated notes."""
    wiki = _wiki(tmp_path)
    outline = "- Priors and likelihood\n- Posterior update\n- Predictive check\n"
    result = curate_from_curriculum(
        wiki,
        curriculum=outline,
        topic="Bayes",
        template="education-concept",
    )
    assert result.get("success") is True
    assert result.get("durable") is True
    notes = result.get("notes") or []
    assert len(notes) == 3
    for n in notes:
        path = n.get("path") or ""
        assert path.replace("\\", "/").startswith("00_Inbox/")
        assert n.get("template") == "education-concept"
        assert n.get("education_tags") is True
        read = wiki.store.read_note(path)
        assert read.get("content") or read.get("body")

    tools = EducationTools(wiki_root=tmp_path / "wiki")
    via = tools.education_wiki_curate_from_curriculum(
        curriculum="- One more bullet about MAP",
        topic="Bayes",
        template="education-method",
    )
    assert via.get("success") is True
    assert via.get("template") == "education-method" or (via.get("notes") or [{}])[0].get("template") == "education-method"


def test_fetch_and_write_failures_do_not_fake_success(tmp_path: Path):
    """[REQ-440-003] Fetch/write failures surface without claiming library update."""
    wiki = _wiki(tmp_path)

    bad_url = curate_from_link(wiki, url="not-a-url", topic="X")
    assert bad_url.get("success") is False
    assert bad_url.get("durable") is False
    assert bad_url.get("notes") == []
    assert "url" in str(bad_url.get("error") or "").lower() or "http" in str(bad_url.get("error") or "").lower()

    def boom(_url: str) -> bytes:
        raise ConnectionError("dns failed")

    fetch_fail = curate_from_link(
        wiki,
        url="https://example.invalid/missing",
        topic="X",
        opener=boom,
    )
    assert fetch_fail.get("success") is False
    assert fetch_fail.get("durable") is False
    assert not fetch_fail.get("path")

    empty = curate_from_curriculum(wiki, curriculum="   \n\n", topic="X")
    assert empty.get("success") is False
    assert empty.get("durable") is False

    # Unauthorized template
    bad_tpl = curate_from_link(
        wiki,
        url="https://example.com/x",
        topic="X",
        template="not-a-real-edu-template",
        body="hello",
    )
    assert bad_tpl.get("success") is False
    assert bad_tpl.get("durable") is False

    # Wiki tools missing
    no_tools = curate_from_link(
        None,
        url="https://example.com/x",
        topic="X",
        body="hello",
        template="education-concept",
    )
    assert no_tools.get("success") is False
    assert no_tools.get("durable") is False


def test_fetch_link_text_success_with_opener():
    html = b"<html><head><title>Demo Page</title></head><body><p>Hello curation</p></body></html>"

    def opener(_url: str) -> bytes:
        return html

    result = fetch_link_text("https://example.com/demo", opener=opener)
    assert result.get("success") is True
    assert "Demo" in str(result.get("title") or "")
    assert "Hello curation" in str(result.get("body") or "")


def test_parse_curriculum_bullets():
    items = parse_curriculum_bullets("1. Alpha\n- Beta\n* Gamma\n\nplain line\n")
    assert items == ["Alpha", "Beta", "Gamma", "plain line"]


def test_education_studio_wiki_chrome_not_removed():
    """[REQ-440-004] Education Studio wiki grounding UI stays."""
    index = Path("src/web/templates/index.html").read_text(encoding="utf-8")
    education_js = Path("src/web/static/modules/studios/education.js").read_text(encoding="utf-8")
    assert 'id="tab-education"' in index
    assert 'id="view-education"' in index
    assert "educationWikiSearchInput" in index or "educationWikiSearchInput" in education_js
    assert "educationWikiHits" in index or "educationWikiHits" in education_js


def test_tutor_pack_lists_curation_tools():
    import json

    pack = json.loads(Path("platform-packs/tutor/pack.json").read_text(encoding="utf-8"))
    skill = next(s for s in pack["skills"] if s["id"] == "education-wiki-curation")
    tools = skill.get("tools") or []
    for name in CURATION_TOOL_NAMES:
        assert name in tools
    for name in ("wiki_note_create", "wiki_note_update", "wiki_template_list"):
        assert name in tools
