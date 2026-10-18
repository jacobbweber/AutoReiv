"""CARD-720: Comprehensive UI audit and button functionality guard contracts."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.guard

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def test_card720_vitest_ui_audit_suite_passes() -> None:
    """Runs the CARD-720 frontend unit suite covering all fixed UI handlers."""
    import os
    import shutil

    env = os.environ.copy()
    if not shutil.which("npx", path=env.get("PATH")):
        extra = Path.home() / ".openclaw" / "tools" / "node-v24.21.0" / "bin"
        if extra.is_dir():
            env["PATH"] = f"{extra}:{env.get('PATH', '')}"
    res = subprocess.run(
        ["npx", "vitest", "run", "tests/unit/frontend/card_720_ui_audit_fixes.test.js"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert res.returncode == 0, f"Vitest failed:\n{res.stdout}\n{res.stderr}"


def test_card720_negative_assertions_no_duplicate_sidebar_or_inverted_copy_toast() -> None:
    """Negative assertions ensuring retired/broken UI wiring patterns stay gone."""
    app_js = _read("src/web/static/app.js")
    desktop_js = _read("src/web/static/modules/ui/agent-desktop.js")
    presets_js = _read("src/web/static/modules/ui/agent_desktop/presets.js")
    projects_js = _read("src/web/static/modules/studios/projects.js")
    obs_js = _read("src/web/static/modules/studios/observability.js")
    edu_html = _read("src/web/templates/partials/prompts_education_skill_studio.html")
    settings_html = _read("src/web/templates/partials/settings_core.html")

    # 1. #toggleSidebarBtn is only bound in chat/scroll.js, never in app.js or agent-desktop.js
    assert "const toggleSidebarBtn = $('toggleSidebarBtn')" not in app_js
    assert "const toggleSidebarBtn = $('toggleSidebarBtn')" not in desktop_js

    # 2. onTalkToForge in app.js targets 'autoreiv', never retired 'forge'
    assert "switchSelectedAgent('forge')" not in app_js
    assert "switchSelectedAgent('autoreiv')" in app_js

    # 3. PRIORITY_TABS in presets.js has 'capabilities' and no retired 'skill-studio' / 'tools-studio'
    assert "'capabilities'" in presets_js
    assert "'skill-studio'" not in presets_js
    assert "'tools-studio'" not in presets_js

    # 4. projectsCopyPathBtn fires its success toast in the try block, not only in catch
    copy_block_start = projects_js.index("const copyPathBtn = $('projectsCopyPathBtn')")
    copy_block = projects_js[copy_block_start : copy_block_start + 650]
    try_part, catch_part = copy_block.split("} catch", 1)
    assert "Copied:" in try_part
    assert "Copied:" not in catch_part

    # 5. observability live log polling checks $('view-observability'), not $query('.tab-view:not(.hidden)')
    assert "$query('.tab-view:not(.hidden)')" not in obs_js

    # 6. Education Due panel has a Hide button (#educationOperatorDueHideBtn)
    assert 'id="educationOperatorDueHideBtn"' in edu_html

    # 7. Settings empty state matches actual button label "Refresh Models"
    assert "Refresh From Providers" not in settings_html
