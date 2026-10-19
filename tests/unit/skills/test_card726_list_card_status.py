"""
CARD-726 unit tests:
1. list_card_status.py parses priority and milestone and normalizes legacy statuses (Complete/Completed/Done (Absorbed) -> Done; Done (Superseded...) -> Superseded).
2. list_card_status.py CLI supports --milestone and --priority filters and displays PRI and MILESTONE columns in table output.
3. card-520-teach-needs-tool.mjs no longer carries obsolete knownBug: 'CARD-535', and smoke.spec.js TC-7 awaits toHaveCSS on #checkForUpdatesBtn.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "card" / "scripts" / "list_card_status.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("list_card_status", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_parse_card_extracts_priority_milestone_and_normalizes_status(tmp_path):
    mod = _load_module()

    c1 = tmp_path / "CARD-901-complete.md"
    c1.write_text(
        "---\nid: CARD-901\ntitle: Legacy complete card\nstatus: Complete\npriority: P1\nmilestone: M31\n---\n# CARD-901 Legacy complete card\n",
        encoding="utf-8",
    )
    parsed1 = mod.parse_card(c1)
    assert parsed1["status"] == "Done"
    assert parsed1["category"] == "closed"
    assert parsed1["priority"] == "P1"
    assert parsed1["milestone"] == "M31"

    c2 = tmp_path / "CARD-902-superseded.md"
    c2.write_text(
        "---\nid: CARD-902\ntitle: Legacy superseded card\nstatus: Done (Superseded by CARD-700)\npriority: P2\nmilestone: M30\n---\n# CARD-902 Legacy superseded card\n",
        encoding="utf-8",
    )
    parsed2 = mod.parse_card(c2)
    assert parsed2["status"] == "Superseded"
    assert parsed2["category"] == "closed"
    assert parsed2["priority"] == "P2"
    assert parsed2["milestone"] == "M30"

    c3 = tmp_path / "CARD-903-absorbed.md"
    c3.write_text(
        "---\nid: CARD-903\ntitle: Legacy absorbed card\nstatus: Done (Absorbed)\n---\n# CARD-903 Legacy absorbed card\n",
        encoding="utf-8",
    )
    parsed3 = mod.parse_card(c3)
    assert parsed3["status"] == "Done"
    assert parsed3["category"] == "closed"


def test_cli_filters_by_milestone_and_priority_and_renders_columns(tmp_path):
    (tmp_path / "CARD-910-alpha.md").write_text(
        "---\nid: CARD-910\ntitle: Alpha M31 P1\nstatus: Ready\npriority: P1\nmilestone: M31\n---\n# CARD-910 Alpha M31 P1\n",
        encoding="utf-8",
    )
    (tmp_path / "CARD-911-beta.md").write_text(
        "---\nid: CARD-911\ntitle: Beta M31 P2\nstatus: Ready\npriority: P2\nmilestone: M31\n---\n# CARD-911 Beta M31 P2\n",
        encoding="utf-8",
    )
    (tmp_path / "CARD-912-gamma.md").write_text(
        "---\nid: CARD-912\ntitle: Gamma M30 P1\nstatus: Done\npriority: P1\nmilestone: M30\n---\n# CARD-912 Gamma M30 P1\n",
        encoding="utf-8",
    )

    res_json = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--cards-dir",
            str(tmp_path),
            "--milestone",
            "M31",
            "--priority",
            "P1",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    rows = json.loads(res_json.stdout)
    assert [r["id"] for r in rows] == ["CARD-910"]

    res_table = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--cards-dir",
            str(tmp_path),
            "--milestone",
            "M31",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "PRI" in res_table.stdout
    assert "MILESTONE" in res_table.stdout
    assert "CARD-910" in res_table.stdout
    assert "CARD-911" in res_table.stdout
    assert "CARD-912" not in res_table.stdout


def test_smoke_tc7_and_card520_hygiene():
    card520 = (REPO_ROOT / "tests" / "e2e" / "journeys" / "card-520-teach-needs-tool.mjs").read_text(encoding="utf-8")
    assert "knownBug: 'CARD-535'" not in card520

    smoke = (REPO_ROOT / "tests" / "e2e" / "smoke.spec.js").read_text(encoding="utf-8")
    assert "await expect(page.locator('#checkForUpdatesBtn')).toHaveCSS('background-color', 'rgb(196, 163, 90)')" in smoke
