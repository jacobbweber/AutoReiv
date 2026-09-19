"""
Regression tests for CARD-382:
Hardened WikiStore Data Resolver and Checkout Working Tree Hygiene.
"""

from pathlib import Path

import pytest

from src.application.skills.wiki_tools import WikiTools
from src.application.wiki.service import WikiService
from src.domain.wiki.store import WikiStore
from src.infrastructure.data.resolver import (
    DataDirResolver,
    is_checkout_live_tree_path,
    repo_root,
)


def test_wikistore_default_resolves_to_user_data_path_card_382():
    """
    CARD-382: Default WikiStore initialization must resolve to DataDirResolver wiki_path
    and never point to the checkout tree.
    """
    expected_wiki = Path(DataDirResolver().resolve().wiki_path).resolve()

    store = WikiStore()
    assert store.root_dir.resolve() == expected_wiki
    assert not is_checkout_live_tree_path(store.root_dir)

    tools = WikiTools()
    assert tools.store.root_dir.resolve() == expected_wiki
    assert not is_checkout_live_tree_path(tools.store.root_dir)

    service = WikiService()
    assert service.store.root_dir.resolve() == expected_wiki
    assert not is_checkout_live_tree_path(service.store.root_dir)


def test_wikistore_scaffold_rejects_checkout_root_card_382():
    """
    CARD-382 Negative assertion: WikiStore.scaffold() must refuse to scaffold inside
    the git checkout root outside scratch/.
    """
    checkout = repo_root()
    rogue_dir = checkout / "unauthorized_wiki"

    store = WikiStore(root_dir=rogue_dir)
    with pytest.raises(ValueError, match="Refusing live data dir inside git checkout"):
        store.scaffold()


def test_checkout_root_contains_no_stray_wiki_folders_card_382(tmp_path: Path, monkeypatch):
    """
    CARD-382 Negative assertion: Running scaffold with default settings creates directories
    in user data and leaves the checkout root completely pristine.
    """
    fake_user_data = tmp_path / "userdata"
    fake_user_data.mkdir(parents=True)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(fake_user_data))
    monkeypatch.delenv("AUTOREIV_WIKI_PATH", raising=False)

    store = WikiStore()
    store.scaffold()

    # User data path must have the scaffolded taxonomy
    assert (fake_user_data / "wiki" / "00_Inbox").is_dir()
    assert (fake_user_data / "wiki" / "01_Notes").is_dir()

    # NEGATIVE ASSERTION: Git checkout root MUST NOT contain any of these folders
    root = repo_root()
    assert not (root / "00_Inbox").exists(), "Defect CARD-382: 00_Inbox leaked into checkout root!"
    assert not (root / "01_Notes").exists(), "Defect CARD-382: 01_Notes leaked into checkout root!"
    assert not (root / "03_Archive").exists(), "Defect CARD-382: 03_Archive leaked into checkout root!"
