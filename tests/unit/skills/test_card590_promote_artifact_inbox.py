"""CARD-590: a promoted artifact with a bare slug lands in 00_Inbox/ (One-Door Policy), not the vault root."""

from __future__ import annotations

import pytest

from src.application.skills.wiki_tools import WikiTools
from src.application.skills.worker_tools import BatchWorkerTools
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def env(tmp_path):
    (tmp_path / "work").mkdir()
    (tmp_path / "work" / "report.csv").write_text("month,revenue\nJan,1\n", encoding="utf-8")
    store = SQLiteStateStore(db_path=str(tmp_path / "t.db"))
    store.initialize_db()
    wiki = WikiTools(wiki_root=tmp_path / "wiki")
    wiki.store.scaffold()
    tools = BatchWorkerTools(state_store=store, wiki_tools=wiki, workspace_root=tmp_path / "work")
    return store, wiki, tools


async def _artifact(store, tools):
    session = store.create_session(agent_id="autoreiv", title="scan")
    res = await tools.batch_worker_scan(session_id=session.id, paths="*.csv", objective="summarize", title="Fixture scan")
    return res["artifact_id"]


@pytest.mark.asyncio
async def test_bare_slug_lands_in_the_inbox(env):
    store, wiki, tools = env
    art = await _artifact(store, tools)
    res = tools.promote_artifact_to_wiki(artifact_id=art, wiki_slug="fixture-scan")
    assert res["success"] is True
    assert res["path"] == "00_Inbox/fixture-scan.md"
    assert (wiki.store.root_dir / "00_Inbox" / "fixture-scan.md").is_file()
    assert not (wiki.store.root_dir / "fixture-scan.md").exists()


@pytest.mark.asyncio
async def test_slug_with_folder_is_kept(env):
    store, wiki, tools = env
    art = await _artifact(store, tools)
    res = tools.promote_artifact_to_wiki(artifact_id=art, wiki_slug="02_Resources/scans/fixture.md")
    assert res["path"] == "02_Resources/scans/fixture.md"



def test_promotion_path_normalizes():
    tools = BatchWorkerTools(state_store=None, wiki_tools=None, workspace_root=".")
    assert tools._promotion_path("scan") == "00_Inbox/scan.md"
    assert tools._promotion_path("scan.md") == "00_Inbox/scan.md"
    assert tools._promotion_path("reports\\audit") == "reports/audit.md"
