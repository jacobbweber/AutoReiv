# The served page stamps app.js?v=<index.html version>-<load time>; restart_serve reports whether it matches.
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _rs():
    spec = importlib.util.spec_from_file_location("restart_serve_stamp", ROOT / "scripts" / "restart_serve.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["restart_serve_stamp"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_served_page_carries_index_version(shared_client):
    rs = _rs()
    index_v = rs.read_app_js_version(ROOT)
    served = rs.parse_app_js_version(shared_client.get("/").text)
    assert served and re.fullmatch(rf"{re.escape(index_v)}-\d+", served)
    assert rs.served_matches(index_v, served)
    urls = set(re.findall(r"/static/app\.js[^\"']*", shared_client.get("/").text))
    assert len(urls) == 1  # modulepreload and script tag use the same URL


def test_served_matches_rejects_other_versions():
    rs = _rs()
    assert rs.served_matches("2.0.103", "2.0.103-1791054941")
    assert not rs.served_matches("2.0.103", "1791054941")
    assert not rs.served_matches("2.0.103", "2.0.102-1791054941")
    assert not rs.served_matches("2.0.103", None)


def test_report_shows_served_and_verify_hint():
    rs = _rs()
    text = rs.format_report(tip="a", branch="b", app_js_v="2.0.103", port=8000, host="0.0.0.0",
                            orphans=[], killed=[], started=True, dry_run=False, served="2.0.103-17")
    assert "served=app.js?v=2.0.103-17 matches_index=True" in text
    assert "app.js?v=2.0.103-<page load time>" in text
