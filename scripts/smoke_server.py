"""CARD-467: launch the Playwright smoke server on scratch data only.

The smoke server must never touch live AppData. The resolver in
``src/infrastructure/data/resolver.py`` picks the data root from the
``AUTOREIV_DATA_DIR`` env, then the live DB's ``data_dir`` setting, then
``%LOCALAPPDATA%\\AutoReiv``, so pinning only the DB and wiki (the old
``playwright.config.js``) still booted packs/skills against live AppData.

This launcher:

1. Force-sets ``AUTOREIV_DATA_DIR`` / ``AUTOREIV_DB_PATH`` / ``AUTOREIV_WIKI_PATH`` /
   ``AUTOREIV_BACKUP_DIR`` under ``<checkout>/scratch/smoke_data`` (ignoring the
   parent shell), and points ``LOCALAPPDATA`` at a fake folder inside it so any
   ``platform_default()`` fallback also stays in scratch.
2. Resolves the real paths with ``DataDirResolver`` and REFUSES to start (exit 2)
   when any of them sits outside ``<checkout>/scratch/`` or inside live AppData.
3. Wipes the smoke data folder (only after the guard passes) and runs uvicorn.

Usage::

    python scripts/smoke_server.py                 # wipe + serve on 127.0.0.1:8765
    python scripts/smoke_server.py --check-only    # print resolved paths, no wipe, no serve
    python scripts/smoke_server.py --check-only --data-dir "%LOCALAPPDATA%\\AutoReiv"   # refused
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Mapping, Optional

CHECKOUT = Path(__file__).resolve().parents[1]
SMOKE_DATA_REL = Path("scratch") / "smoke_data"
FAKE_LOCALAPPDATA_NAME = "_localappdata"
EXIT_REFUSED = 2

ENV_DATA_DIR = "AUTOREIV_DATA_DIR"
ENV_DB_PATH = "AUTOREIV_DB_PATH"
ENV_WIKI_PATH = "AUTOREIV_WIKI_PATH"
ENV_BACKUP_DIR = "AUTOREIV_BACKUP_DIR"


def _norm(path: Path | str) -> Path:
    return Path(os.path.normcase(os.path.abspath(os.path.expanduser(str(path)))))


def is_within(path: Path | str, parent: Path | str) -> bool:
    """True when ``path`` equals or sits under ``parent`` (case-insensitive on Windows)."""
    p, root = _norm(path), _norm(parent)
    return p == root or root in p.parents


def live_data_roots(
    env: Optional[Mapping[str, str]] = None,
    *,
    home: Optional[Path] = None,
) -> list[Path]:
    """Real user-data roots that tests must never touch.

    ``%LOCALAPPDATA%\\AutoReiv`` (Windows default), ``~/.autoreiv`` (POSIX default),
    and the ``data_dir`` setting stored in the live DB when one is set.
    """
    env = os.environ if env is None else env
    home = Path.home() if home is None else home
    roots: list[Path] = []
    local_appdata = env.get("LOCALAPPDATA")
    if local_appdata:
        roots.append(Path(local_appdata) / "AutoReiv")
    else:
        roots.append(home / "AppData" / "Local" / "AutoReiv")
    roots.append(home / ".autoreiv")
    for root in list(roots):
        setting = _read_live_data_dir_setting(root / "database" / "autoreiv.db")
        if setting:
            roots.append(Path(setting))
    return roots


def _read_live_data_dir_setting(db_path: Path) -> Optional[str]:
    if not db_path.is_file():
        return None
    try:
        import sqlite3

        conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        try:
            row = conn.execute("SELECT value_json FROM settings WHERE key = 'data_dir'").fetchone()
        finally:
            conn.close()
    except Exception:
        return None
    if not row or row[0] is None:
        return None
    import json

    try:
        value = json.loads(row[0])
    except (TypeError, ValueError):
        value = row[0]
    return value.strip() if isinstance(value, str) and value.strip() else None


def live_data_problems(
    paths: Mapping[str, Path | str],
    forbidden_roots: Iterable[Path | str],
    *,
    required_parent: Optional[Path | str] = None,
) -> list[str]:
    """Return one message per path that is inside live data or outside ``required_parent``."""
    forbidden = [Path(r) for r in forbidden_roots]
    problems: list[str] = []
    for name, raw in paths.items():
        if raw is None:
            continue
        path = Path(raw)
        for root in forbidden:
            if is_within(path, root):
                problems.append(f"{name} = {path} is inside live user data {root}")
                break
        else:
            if required_parent is not None and not is_within(path, required_parent):
                problems.append(f"{name} = {path} is outside {Path(required_parent)}")
    return problems


def build_smoke_env(
    base_env: Mapping[str, str],
    data_dir: Path,
) -> dict[str, str]:
    """Copy ``base_env`` and force every AutoReiv data path under ``data_dir``."""
    env = dict(base_env)
    env[ENV_DATA_DIR] = str(data_dir)
    env[ENV_DB_PATH] = str(data_dir / "database" / "autoreiv.db")
    env[ENV_WIKI_PATH] = str(data_dir / "wiki")
    env[ENV_BACKUP_DIR] = str(data_dir / "backups")
    env["LOCALAPPDATA"] = str(data_dir / FAKE_LOCALAPPDATA_NAME)
    return env


def resolve_paths(env: Mapping[str, str], checkout: Path = CHECKOUT) -> dict[str, Path]:
    """Resolve the paths the app would use under ``env`` (same resolver as serve)."""
    if str(checkout) not in sys.path:
        sys.path.insert(0, str(checkout))
    from src.infrastructure.data.resolver import DataDirResolver

    keys = (ENV_DATA_DIR, ENV_DB_PATH, ENV_WIKI_PATH, ENV_BACKUP_DIR)
    saved = {k: os.environ.get(k) for k in keys}
    try:
        for k in keys:
            if env.get(k):
                os.environ[k] = env[k]
            else:
                os.environ.pop(k, None)
        resolver = DataDirResolver(checkout_root=checkout, local_appdata=env.get("LOCALAPPDATA"))
        resolved = resolver.resolve()
        return {
            "platform_default": resolver.platform_default(),
            "root": resolved.root,
            "db_path": resolved.db_path,
            "wiki_path": resolved.wiki_path,
            "skills_path": resolved.skills_path,
            "agents_path": resolved.agents_path,
            "packs_path": resolved.packs_path,
            "backups_path": resolved.backups_path,
            "job_templates_path": resolved.job_templates_path,
        }
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def wipe_smoke_dir(data_dir: Path, checkout: Path = CHECKOUT) -> None:
    """Delete ``data_dir`` - only ever under ``<checkout>/scratch/`` (never the scratch root)."""
    scratch = checkout / "scratch"
    if not is_within(data_dir, scratch) or _norm(data_dir) == _norm(scratch):
        raise ValueError(f"Refusing to wipe {data_dir}: not a folder under {scratch}")
    if data_dir.exists():
        shutil.rmtree(data_dir)


def _parse(argv: Optional[list[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CARD-467 scratch-only smoke server launcher")
    parser.add_argument("--check-only", action="store_true", help="resolve and guard only; no wipe, no serve")
    parser.add_argument("--data-dir", default=None, help="smoke data folder (default scratch/smoke_data)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default="8765")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None, *, checkout: Path = CHECKOUT, runner=subprocess.call) -> int:
    args = _parse(argv)
    data_dir = Path(args.data_dir).expanduser() if args.data_dir else SMOKE_DATA_REL
    if not data_dir.is_absolute():
        data_dir = checkout / data_dir
    data_dir = Path(os.path.abspath(data_dir))

    forbidden = live_data_roots(os.environ)
    env = build_smoke_env(os.environ, data_dir)
    paths = resolve_paths(env, checkout)
    paths["fake_localappdata"] = Path(env["LOCALAPPDATA"])
    problems = live_data_problems(paths, forbidden, required_parent=checkout / "scratch")

    for name, value in paths.items():
        print(f"[smoke-server] {name:<18} {value}")
    if problems:
        print("[smoke-server] REFUSED: smoke data must live under scratch/ and never in live AppData.", file=sys.stderr)
        for msg in problems:
            print(f"[smoke-server]   - {msg}", file=sys.stderr)
        return EXIT_REFUSED
    if args.check_only:
        print("[smoke-server] OK: all paths under scratch/ (check-only; nothing wiped or started)")
        return 0

    wipe_smoke_dir(data_dir, checkout)
    print(f"[smoke-server] wiped {data_dir}; starting uvicorn on {args.host}:{args.port}")
    cmd = [sys.executable, "-m", "uvicorn", "src.web.app:app", "--host", args.host, "--port", str(args.port)]
    try:
        return int(runner(cmd, env=env, cwd=str(checkout)))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
