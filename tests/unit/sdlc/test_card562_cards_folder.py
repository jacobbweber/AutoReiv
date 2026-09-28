"""CARD-562: cards live in .agents/cards/ (repo, card tools, checkout detection)."""

import subprocess
from pathlib import Path

from src.application.sdlc.paths import autoreiv_checkout_roots, detect_autoreiv_root
from src.application.skills.card_tools import CardTools

REPO = Path(__file__).resolve().parents[3]

CARD = "---\nid: CARD-7\ntitle: t\nstatus: Ready\n---\n# CARD-7 t\n"


def test_repo_keeps_cards_only_in_agents_cards():
    tracked = subprocess.run(
        ["git", "ls-files", "docs/cards", ".github/cards"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.split()
    assert tracked == [], f"cards outside .agents/cards: {tracked[:5]}"
    assert any((REPO / ".agents" / "cards").glob("CARD-*.md"))


def test_checkout_detected_with_only_agents_cards(tmp_path: Path):
    co = tmp_path / "checkout"
    (co / ".agents" / "cards").mkdir(parents=True)
    (co / "AGENTS.md").write_text("# a\n", encoding="utf-8")
    (co / "src").mkdir()
    assert detect_autoreiv_root(co / "src") == co.resolve()
    assert co.resolve() in autoreiv_checkout_roots({"AUTOREIV_CHECKOUT_ROOT": str(co)})


def test_real_repo_detected_from_its_own_tree():
    assert detect_autoreiv_root(REPO / "src") == REPO


def test_new_project_card_written_to_agents_cards(tmp_path: Path):
    res = CardTools(default_project_root=str(tmp_path)).write_card(content=CARD, filename="CARD-7-t.md")
    assert res["success"] is True
    assert (tmp_path / ".agents" / "cards" / "CARD-7-t.md").is_file()
    assert not (tmp_path / "docs" / "cards").exists()


def test_older_project_card_still_readable_from_docs_cards(tmp_path: Path):
    (tmp_path / "docs" / "cards").mkdir(parents=True)
    (tmp_path / "docs" / "cards" / "CARD-7-t.md").write_text(CARD, encoding="utf-8")
    assert CardTools(default_project_root=str(tmp_path)).read_card(card_id="CARD-7")["success"] is True
