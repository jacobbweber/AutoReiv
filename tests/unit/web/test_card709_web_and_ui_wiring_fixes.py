"""CARD-709: Web and UI wiring fixes:
1. study_entry.js targets #promptInput (not only #chatInput) and does not double-bind conflicting bubble + capture listeners on Due/Progress/Curate buttons.
2. PUT /api/settings/wiki-path refreshes request.app.state.wiki_service immediately and wiki.py has no hardcoded './data/wiki' fallback.
3. save_mcp_server resolves data_dir from app.state.data_dir_paths when app.state.data_dir is unset.
4. settings.js passes unsaved API key in X-Provider-Api-Key header (never in GET query string) and discover_models accepts X-Provider-Api-Key.
5. test_remote_host runs _probe_ssh via asyncio.to_thread so it never blocks the event loop.
6. chat.js and projects.js bind the active project pill and Pair button to 'autoreiv', and api.sessions uses /api/sessions.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_study_entry_targets_prompt_input_and_avoids_shadowed_button_listeners():
    """study_entry.js must resolve #promptInput for composer prefills and not attach conflicting bubble+capture click listeners."""
    study_js = (REPO_ROOT / "src/web/static/modules/studios/study_entry.js").read_text(encoding="utf-8")
    assert "promptInput" in study_js
    # Must not attach both openProgressInEducationMode bubble listener AND deepLinkStudio capture listener to chatEducationModeProgressBtn
    init_block = study_js.split("export function initStudyEntry", 1)[1]
    assert "progressBtn.addEventListener" not in init_block
    assert "dueBtn.addEventListener" not in init_block
    assert "curateBtn.addEventListener" not in init_block


@pytest.mark.asyncio
async def test_put_wiki_path_refreshes_live_wiki_service_and_no_hardcoded_fallback(tmp_path: Path):
    """PUT /api/settings/wiki-path must refresh request.app.state.wiki_service and wiki.py must not hardcode './data/wiki'."""
    from src.application.wiki.service import WikiService
    from src.web.routers.settings_data_backup import WikiPathBody, put_wiki_path
    from src.web.routers.wiki import _get_wiki_service

    wiki_py = (REPO_ROOT / "src/web/routers/wiki.py").read_text(encoding="utf-8")
    assert '"./data/wiki"' not in wiki_py
    assert "'./data/wiki'" not in wiki_py

    old_wiki = tmp_path / "old_wiki"
    new_wiki = tmp_path / "new_wiki"
    old_wiki.mkdir(parents=True)

    fake_store = MagicMock()
    state = SimpleNamespace(
        store=fake_store,
        wiki_path=str(old_wiki),
        wiki_service=WikiService(wiki_root=str(old_wiki)),
        data_dir_paths=SimpleNamespace(root=tmp_path, wiki_path=old_wiki),
    )
    request = SimpleNamespace(app=SimpleNamespace(state=state))

    res = await put_wiki_path(request, WikiPathBody(path=str(new_wiki), confirm_scaffold=True))
    assert res["status"] == "updated"

    live_service = _get_wiki_service(request)
    assert Path(live_service.store.root_dir).resolve() == new_wiki.resolve()


@pytest.mark.asyncio
async def test_save_mcp_server_resolves_data_dir_from_data_dir_paths(tmp_path: Path):
    """save_mcp_server must pass data_dir from app.state.data_dir_paths.root to author_mcp_companion_skill."""
    from src.domain.settings.models import MCPServerConfig
    from src.web.routers.settings import save_mcp_server

    fake_store = MagicMock()
    fake_store.get_setting.return_value = []
    state = SimpleNamespace(
        store=fake_store,
        mcp_manager=MagicMock(),
        data_dir_paths=SimpleNamespace(root=tmp_path),
    )
    request = SimpleNamespace(app=SimpleNamespace(state=state))
    cfg = MCPServerConfig(name="demo_mcp", transport="sse", url="http://127.0.0.1:9999/sse", enabled=True)

    captured_data_dir = []

    def _fake_author(*, server_name, tools, url, data_dir):
        captured_data_dir.append(data_dir)

    with (
        patch(
            "src.web.routers.settings.reconcile_saved_mcp_server",
            return_value={"mounted": True, "tools": [{"name": "demo_tool", "description": "Demo"}], "failure": None},
        ),
        patch("src.infrastructure.mcp.companion_author.author_mcp_companion_skill", side_effect=_fake_author),
    ):
        await save_mcp_server(request, cfg)

    assert captured_data_dir == [str(tmp_path)]


@pytest.mark.asyncio
async def test_discover_models_uses_header_not_query_string_for_api_key():
    """settings.js must not put api_key in the URL query string, and discover_models must read X-Provider-Api-Key."""
    from src.web.routers.settings import discover_models

    settings_js = (REPO_ROOT / "src/web/static/modules/studios/settings.js").read_text(encoding="utf-8")
    assert "&api_key=" not in settings_js
    assert "X-Provider-Api-Key" in settings_js

    registered_adapters = []
    fake_gateway = MagicMock()
    fake_gateway.default_provider_id = "openai"
    fake_gateway.register_provider.side_effect = lambda a: registered_adapters.append(a)
    fake_gateway.list_models = MagicMock(return_value=asyncio.Future())
    fake_gateway.list_models.return_value.set_result([])

    fake_hw = MagicMock()
    fake_hw.evaluate_models.return_value = []

    state = SimpleNamespace(gateway=fake_gateway, hw_calc=fake_hw, store=None)
    request = SimpleNamespace(
        app=SimpleNamespace(state=state),
        headers={"x-provider-api-key": "sk-header-secret-key"},
    )

    await discover_models(
        request=request,
        provider_id="openai",
        host_url="https://api.openai.com/v1",
        api_key=None,
    )
    assert len(registered_adapters) == 1
    assert getattr(registered_adapters[0], "api_key", None) == "sk-header-secret-key"


@pytest.mark.asyncio
async def test_remote_host_probe_runs_in_worker_thread():
    """test_remote_host must offload _probe_ssh via asyncio.to_thread instead of blocking the event loop."""
    from src.web.routers import remote_hosts

    fake_store = MagicMock()
    fake_host = SimpleNamespace(id="h1", name="Host 1")
    fake_store.get_remote_host.return_value = fake_host
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(store=fake_store)))

    to_thread_calls = []

    async def _spy_to_thread(func, *args, **kwargs):
        to_thread_calls.append((func, args, kwargs))
        return True, 12, "Connected"

    with patch("src.web.routers.remote_hosts.asyncio.to_thread", side_effect=_spy_to_thread):
        res = await remote_hosts.test_remote_host(request, "h1")

    assert res["status"] == "ok"
    assert len(to_thread_calls) == 1
    assert to_thread_calls[0][0] is remote_hosts._probe_ssh


def test_chat_projects_and_api_js_wiring():
    """chat.js and projects.js must wire active project pill to 'autoreiv' and '/api/projects/selected' [CARD-709, CARD-740], and api.sessions must use /api/sessions."""
    chat_js = (REPO_ROOT / "src/web/static/modules/studios/chat.js").read_text(encoding="utf-8")
    projects_js = (REPO_ROOT / "src/web/static/modules/studios/projects.js").read_text(encoding="utf-8")
    api_js = (REPO_ROOT / "src/web/static/modules/services/api.js").read_text(encoding="utf-8")

    assert "state.selectedAgentId === 'autoreiv'" in chat_js
    assert "'/api/projects/selected'" in projects_js
    assert "projectsPairDeveloperBtn" not in projects_js
    assert "api.get('/api/sessions'" in api_js
