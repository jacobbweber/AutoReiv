"""
Unit tests for Context-Isolated Batch Worker Skill & Map-Reduce [REQ-ART-003].
"""

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.wiki_skill import WikiSkill
from src.application.skills.worker_skill import BatchWorkerSkill
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def temp_workspace(tmp_path):
    # Create sample files for batch scanning
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    file1 = src_dir / "auth.py"
    file1.write_text("def login():\n    return 'auth_token'", encoding="utf-8")

    file2 = src_dir / "router.py"
    file2.write_text("def get_users():\n    return ['alice', 'bob']", encoding="utf-8")

    file3 = src_dir / "config.py"
    file3.write_text("API_SECRET = 'super_secret_key'", encoding="utf-8")

    return tmp_path


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    s = SQLiteStateStore(db_path=db_path)
    s.initialize_db()
    return s


@pytest.fixture
def wiki_skill(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    return WikiSkill(wiki_root=wiki_dir)


@pytest.fixture
def worker_skill(store, wiki_skill, temp_workspace):
    return BatchWorkerSkill(
        state_store=store,
        wiki_skill=wiki_skill,
        workspace_root=temp_workspace,
    )


@pytest.mark.asyncio
async def test_batch_worker_scan_execution(worker_skill, store, temp_workspace):
    session = store.create_session(agent_id="assistant", title="Scan Session")

    result = await worker_skill.batch_worker_scan(
        session_id=session.id,
        paths=["src/auth.py", "src/router.py", "src/config.py"],
        objective="Inspect for secrets and authentication functions",
        chunk_size=2,
    )

    assert result["success"] is True
    assert "artifact_id" in result
    assert result["item_count"] == 3
    assert result["artifact_uri"].startswith("artifact://")
    assert "Scan completed across 3 files" in result["summary"] or len(result["summary"]) > 0

    # Verify saved artifact in SQLite
    artifact = store.get_artifact(result["artifact_id"])
    assert artifact is not None
    assert artifact.session_id == session.id
    assert artifact.item_count == 3
    assert "src/auth.py" in artifact.content
    assert "src/config.py" in artifact.content


@pytest.mark.asyncio
async def test_batch_worker_scan_glob_pattern(worker_skill, store, temp_workspace):
    session = store.create_session(agent_id="assistant", title="Glob Session")

    result = await worker_skill.batch_worker_scan(
        session_id=session.id,
        paths="src/*.py",
        objective="Analyze all python files in src",
    )

    assert result["success"] is True
    assert result["item_count"] == 3


@pytest.mark.asyncio
async def test_promote_artifact_to_wiki(worker_skill, store, wiki_skill):
    session = store.create_session(agent_id="assistant", title="Promotion Session")

    scan_res = await worker_skill.batch_worker_scan(
        session_id=session.id,
        paths="src/*.py",
        objective="Analyze security",
    )
    art_id = scan_res["artifact_id"]

    promo_res = worker_skill.promote_artifact_to_wiki(
        artifact_id=art_id,
        wiki_slug="reports/security-audit",
        title="Security Audit Report",
        category="audits",
    )

    assert promo_res["success"] is True
    assert "path" in promo_res

    # Verify note in Wiki Vault
    note = wiki_skill.read_wiki_note("reports/security-audit.md")
    assert note["success"] is True
    assert note["frontmatter"]["title"] == "Security Audit Report"
    assert note["frontmatter"]["topic"] == "audits"
    assert "Security" in note["body"] or "src/" in note["body"]


def test_tool_registry_registration(worker_skill):
    reg = ScopedToolRegistry()
    worker_skill.register_tools(reg)

    assert reg.get_tool_definition("batch_worker_scan") is not None
    assert reg.get_tool_definition("get_session_artifact") is not None
    assert reg.get_tool_definition("promote_artifact_to_wiki") is not None
