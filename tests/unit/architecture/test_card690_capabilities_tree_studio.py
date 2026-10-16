"""
Guard tests for CARD-690 / ADR-0065 (Slice 4):
Unified Capabilities directory tree studio (`#view-capabilities`, `#dock-capabilities`, `capabilities_studio.js`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.guard

ROOT = Path(__file__).resolve().parents[3]


def test_adr0065_capabilities_studio_registered_in_html_dock_and_app():
    """ADR-0065 Slice 4: index.html, agent-desktop.js, and app.js register the Capabilities directory tree studio."""
    index_html = (ROOT / "src" / "web" / "templates" / "index.html").read_text(encoding="utf-8")
    assert 'id="tab-capabilities"' in index_html
    assert 'id="view-capabilities"' in index_html
    assert 'id="capabilitiesTreePane"' in index_html
    assert 'id="capabilitiesInspectorPane"' in index_html
    assert 'id="capabilitiesFileEditor"' in index_html
    assert 'id="capabilitiesSaveFileBtn"' in index_html

    desktop_js = (ROOT / "src" / "web" / "static" / "modules" / "ui" / "agent-desktop.js").read_text(encoding="utf-8")
    assert "id: 'dock-capabilities'" in desktop_js
    assert "tab: 'capabilities'" in desktop_js
    assert "capabilities: 'view-capabilities'" in desktop_js

    app_js = (ROOT / "src" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    assert "initCapabilitiesStudio" in app_js
    assert "studioRegistry.register('capabilities'" in app_js


def test_adr0065_capabilities_studio_uses_services_api_and_has_no_inline_onclick():
    """Frontend rules: API calls go through services/api.js and studio markup contains no inline onclick."""
    api_js = (ROOT / "src" / "web" / "static" / "modules" / "services" / "api.js").read_text(encoding="utf-8")
    assert "/api/capabilities/tree" in api_js
    assert "/api/capabilities/skills/" in api_js

    studio_path = ROOT / "src" / "web" / "static" / "modules" / "studios" / "capabilities_studio.js"
    model_path = ROOT / "src" / "web" / "static" / "modules" / "studios" / "capabilities_tree_model.js"
    assert studio_path.is_file(), "capabilities_studio.js must exist"
    assert model_path.is_file(), "capabilities_tree_model.js must exist"

    studio_src = studio_path.read_text(encoding="utf-8")
    model_src = model_path.read_text(encoding="utf-8")
    assert "onclick=" not in studio_src.lower()
    assert "onclick=" not in model_src.lower()
    assert "from '../services/api.js'" in studio_src
    assert "fetch(" not in studio_src
