"""CARD-692 Guard Test: Capabilities Studio consolidation, MCP tree node, deep-link routing, and dock cleanup.

Invariants enforced:
1. `DOCK_LAUNCHERS` in `src/web/static/modules/ui/agent-desktop.js` exposes `dock-capabilities`
   and does NOT include `dock-skill-studio` or `dock-tools-studio`.
2. `#sidebarNav` in `src/web/templates/index.html` exposes `#tab-capabilities` and does NOT
   include `#tab-skill-studio` or `#tab-tools-studio`.
3. `#view-capabilities` in `src/web/templates/index.html` includes `#capabilitiesMcpPane` for
   managing platform and per-agent MCP servers directly from the `mcp/` tree node.
4. `openSkillStudio` and `openToolsStudio` in `src/web/static/app.js` route into
   `openCapabilitiesStudio` (`switchTab('capabilities')`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.guard

REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def test_dock_and_sidebar_expose_only_capabilities_launcher():
    desktop_js = _read("src/web/static/modules/ui/agent-desktop.js")
    assert "id: 'dock-capabilities'" in desktop_js
    assert "id: 'dock-skill-studio'" not in desktop_js
    assert "id: 'dock-tools-studio'" not in desktop_js

    html = _read("src/web/templates/index.html")
    sidebar_start = html.index('id="sidebarNav"')
    sidebar_end = html.index('id="view-chat"')
    sidebar_html = html[sidebar_start:sidebar_end]
    assert 'id="tab-capabilities"' in sidebar_html
    assert 'id="tab-skill-studio"' not in sidebar_html
    assert 'id="tab-tools-studio"' not in sidebar_html


def test_capabilities_studio_hosts_mcp_node_and_inspector_pane():
    html = _read("src/web/templates/index.html")
    cap_start = html.index('id="view-capabilities"')
    cap_html = html[cap_start:]
    assert 'id="capabilitiesMcpPane"' in cap_html
    assert 'id="capabilitiesMcpScopeSelect"' in cap_html
    assert 'id="capabilitiesMcpList"' in cap_html
    assert 'id="capabilitiesMcpSaveBtn"' in cap_html

    tree_model = _read("src/web/static/modules/studios/capabilities_tree_model.js")
    assert "MCP_TREE_NODE_ID" in tree_model
    assert "select-mcp-node" in tree_model


def test_app_deep_links_route_skill_and_tools_studio_to_capabilities():
    app_js = _read("src/web/static/app.js")
    assert "openCapabilitiesStudio" in app_js
    # openSkillStudio and openToolsStudio delegate to openCapabilitiesStudio
    open_skill_idx = app_js.index("openSkillStudio:")
    open_tools_idx = app_js.index("openToolsStudio:")
    block = app_js[open_skill_idx : open_tools_idx + 350]
    assert "openCapabilitiesStudio(" in block
    assert "switchTab('skill-studio')" not in block
    assert "switchTab('tools-studio')" not in block
