"""Restart AutoReiv serve with orphan hygiene [CARD-256].

Find listener(s) on a port (default 8000), optionally kill them, start one fresh
serve from the current branch tip, and print tip SHA + app.js?v= from index.html.
The server serves app.js?v=<index version>-<page load time>; after a start the
script reads the served page and reports whether it carries the index version.

Usage:
  python scripts/restart_serve.py --dry-run
  python scripts/restart_serve.py --port 8000
  python scripts/restart_serve.py --kill-only
  python scripts/restart_serve.py --status
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

APP_JS_VERSION_RE = re.compile(
    r"""['\"]/static/app\.js\?v=([^'\"]+)['\"]""",
    re.IGNORECASE,
)
DEFAULT_PORT = 8000
DEFAULT_HOST = "0.0.0.0"
INDEX_REL = Path("src/web/templates/index.html")


def repo_root(start: Optional[Path] = None) -> Path:
    """Resolve repo root (directory containing src/web/templates/index.html)."""
    here = (start or Path(__file__).resolve()).parent
    candidates = [here, here.parent, Path.cwd()]
    for base in candidates:
        if (base / INDEX_REL).is_file():
            return base.resolve()
        if (base.parent / INDEX_REL).is_file():
            return base.parent.resolve()
    cur = Path.cwd().resolve()
    for p in [cur, *cur.parents]:
        if (p / INDEX_REL).is_file():
            return p
    raise FileNotFoundError(f"Could not locate {INDEX_REL} from {Path.cwd()}")


def parse_app_js_version(html: str) -> Optional[str]:
    """Extract cache-bust version from index.html script tag."""
    m = APP_JS_VERSION_RE.search(html)
    return m.group(1) if m else None


def read_app_js_version(root: Path) -> str:
    html = (root / INDEX_REL).read_text(encoding="utf-8")
    ver = parse_app_js_version(html)
    if not ver:
        raise ValueError(f"No versioned app.js?v= found in {INDEX_REL}")
    return ver


def tip_sha(root: Path) -> str:
    out = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=str(root),
        text=True,
    )
    return out.strip()


def tip_branch(root: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(root),
            text=True,
        )
        return out.strip()
    except subprocess.CalledProcessError:
        return "UNKNOWN"


def _pids_from_netstat(port: int) -> List[int]:
    pids: set[int] = set()
    try:
        out = subprocess.check_output(["netstat", "-ano"], text=True, errors="replace")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    for line in out.splitlines():
        cols = line.split()
        if len(cols) < 5:
            continue
        proto = cols[0].upper()
        if not proto.startswith("TCP"):
            continue
        local, state, pid_s = cols[1], cols[3], cols[-1]
        if state.upper() != "LISTENING":
            continue
        if local.endswith(f":{port}") and pid_s.isdigit():
            pids.add(int(pid_s))
    return sorted(pids)


def find_listener_pids(port: int) -> List[int]:
    """Return PIDs listening on TCP port (Windows-first; Linux fallback)."""
    pids: set[int] = set()
    if sys.platform.startswith("win"):
        try:
            ps = (
                f"(Get-NetTCPConnection -LocalPort {int(port)} -State Listen "
                f"-ErrorAction SilentlyContinue).OwningProcess"
            )
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            for line in out.splitlines():
                line = line.strip()
                if line.isdigit():
                    pids.add(int(line))
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        if not pids:
            pids.update(_pids_from_netstat(port))
    else:
        for cmd in (
            ["ss", "-ltnp", f"sport = :{port}"],
            ["lsof", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
        ):
            try:
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
            for m in re.finditer(r"pid=(\d+)", out):
                pids.add(int(m.group(1)))
            for line in out.splitlines():
                line = line.strip()
                if line.isdigit():
                    pids.add(int(line))
            if pids:
                break
    return sorted(pids)


def kill_pids(pids: Sequence[int], *, dry_run: bool = False) -> List[int]:
    killed: List[int] = []
    for pid in pids:
        if dry_run:
            killed.append(pid)
            continue
        if sys.platform.startswith("win"):
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F", "/T"],
                check=False,
                capture_output=True,
            )
        else:
            subprocess.run(["kill", "-TERM", str(pid)], check=False, capture_output=True)
        killed.append(pid)
    return killed


def health_check_host(bind_host: str) -> str:
    """Loopback health when bind is all-interfaces (0.0.0.0 / ::)."""
    h = (bind_host or "").strip()
    if h in ("0.0.0.0", "::", "[::]"):
        return "127.0.0.1"
    return h or "127.0.0.1"


SHELL_ENV_PREFIX = "AUTOREIV_"


def read_dotenv(root: Path) -> Dict[str, str]:
    """KEY=VALUE pairs of the repo .env (same rules as load_repo_dotenv); empty when there is none."""
    path = Path(root) / ".env"
    out: Dict[str, str] = {}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, val = stripped.partition("=")
        key = key.strip()
        if key:
            out[key] = val.strip().strip('"').strip("'")
    return out


def serve_child_env(
    base: Mapping[str, str],
    root: Path,
    *,
    data_dir: Optional[str] = None,
    wiki_path: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Tuple[Dict[str, str], List[str]]:
    """Environment for the serve this script starts, and the shell AUTOREIV_* names it ignored [CARD-683].

    The calling shell's AUTOREIV_* variables are never passed on: a shell left pointing at a throwaway data
    folder must not move the real serve onto it. The serve's AutoReiv configuration is the repo .env plus the
    explicit parameters (--data-dir, --wiki-path, --db-path); otherwise its configured or default live folder.
    Other variables (PATH and so on) are kept, and the shell still wins over .env for them as before.
    """
    dropped = sorted(k for k in base if k.upper().startswith(SHELL_ENV_PREFIX))
    env = {k: v for k, v in base.items() if not k.upper().startswith(SHELL_ENV_PREFIX)}
    for key, val in read_dotenv(root).items():
        env.setdefault(key, val)
    for key, val in (("AUTOREIV_DATA_DIR", data_dir), ("AUTOREIV_WIKI_PATH", wiki_path), ("AUTOREIV_DB_PATH", db_path)):
        if val:
            env[key] = str(val)
    return env, dropped


def resolve_data_paths(env: Mapping[str, str], root: Path) -> Dict[str, str]:
    """The data folder, database and wiki a serve started with ``env`` resolves (CARD-683 report line)."""
    from unittest.mock import patch

    root = Path(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        home = Path.home()  # from this process: the child env may not carry USERPROFILE / HOME
        with patch.dict(os.environ, dict(env), clear=True):
            from src.infrastructure.data.resolver import DataDirResolver

            paths = DataDirResolver(checkout_root=root, home=home).resolve()
        return {"data_dir": str(paths.root), "db": str(paths.db_path), "wiki": str(paths.wiki_path)}
    except Exception as exc:  # noqa: BLE001 - the report must not stop a restart
        return {"data_dir": f"unknown ({exc})", "db": "", "wiki": ""}


def start_serve(
    root: Path,
    *,
    host: str,
    port: int,
    dry_run: bool = False,
    log_path: Optional[Path] = None,
    reload: bool = True,
    child_env: Optional[Mapping[str, str]] = None,
) -> Optional[subprocess.Popen]:
    """Start one detached serve from repo tip. Returns Popen or None on dry-run."""
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "src.cli.main",
        "serve",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        cmd.append("--reload")
    if dry_run:
        return None
    log_path = log_path or (root / ".autoreiv-restart-serve.log")
    log_f = open(log_path, "a", encoding="utf-8")
    creation = 0
    if child_env is None:  # CARD-683: never the calling shell's AUTOREIV_* variables
        child_env, _ = serve_child_env(os.environ, root)
    kwargs = {
        "cwd": str(root),
        "stdout": log_f,
        "stderr": subprocess.STDOUT,
        "env": dict(child_env),
    }
    if sys.platform.startswith("win"):
        creation = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200) | getattr(
            subprocess, "DETACHED_PROCESS", 0x00000008
        )
        kwargs["creationflags"] = creation
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs)


def wait_health(host: str, port: int, tries: int = 40) -> bool:
    import urllib.request

    url = f"http://{host}:{port}/api/health"
    for _ in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def served_app_js_version(host: str, port: int) -> Optional[str]:
    """app.js version in the page the running serve returns (None when it cannot be read)."""
    import urllib.request

    try:
        with urllib.request.urlopen(f"http://{host}:{port}/", timeout=5) as resp:
            return parse_app_js_version(resp.read().decode("utf-8", "replace"))
    except Exception:
        return None


def served_matches(app_js_v: str, served: Optional[str]) -> bool:
    """The served stamp is <index version>-<load time> (src/web/app.py)."""
    return bool(served) and (served == app_js_v or served.startswith(f"{app_js_v}-"))


def format_report(
    *,
    tip: str,
    branch: str,
    app_js_v: str,
    port: int,
    host: str,
    orphans: Iterable[int],
    killed: Iterable[int],
    started: bool,
    dry_run: bool,
    served: Optional[str] = None,
    data: Optional[Mapping[str, str]] = None,
    dropped: Sequence[str] = (),
) -> str:
    lines = [
        f"branch={branch}",
        f"tip_sha={tip}",
        f"app.js?v={app_js_v}",
        f"port={port}",
        f"host={host}",
        f"orphans_found={list(orphans)}",
        f"killed={list(killed)}",
        f"started={started}",
        f"dry_run={dry_run}",
    ]
    if data is not None:  # CARD-683: the data folder the serve uses
        lines.append(f"data_dir={data.get('data_dir', '')}")
        lines.append(f"db={data.get('db', '')}")
        lines.append(f"wiki={data.get('wiki', '')}")
    if dropped:
        lines.append(f"ignored_shell_env={list(dropped)}")
    if served is not None:
        lines.append(f"served=app.js?v={served} matches_index={served_matches(app_js_v, served)}")
    lines.append(f"verify=Ctrl+F5 then confirm Network shows app.js?v={app_js_v}-<page load time>")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="CARD-256 serve/orphan hygiene restart helper")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--dry-run", action="store_true", help="Report only; do not kill or start")
    p.add_argument("--kill-only", action="store_true", help="Kill orphans; do not start serve")
    p.add_argument("--status", action="store_true", help="Print tip/version/listeners; no mutate")
    p.add_argument("--no-wait", action="store_true", help="Do not wait for /api/health after start")
    p.add_argument("--no-reload", action="store_true", help="Start without uvicorn --reload")
    p.add_argument("--root", type=Path, default=None, help="Repo root override")
    p.add_argument("--data-dir", default=None, help="Data folder for the serve (else .env, setting or default)")
    p.add_argument("--wiki-path", default=None, help="Wiki folder for the serve (else from the data folder)")
    p.add_argument("--db-path", default=None, help="Database file for the serve (else from the data folder)")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    root = Path(args.root).resolve() if args.root else repo_root()
    tip = tip_sha(root)
    branch = tip_branch(root)
    app_js_v = read_app_js_version(root)
    orphans = find_listener_pids(args.port)
    child_env, dropped = serve_child_env(
        os.environ, root, data_dir=args.data_dir, wiki_path=args.wiki_path, db_path=args.db_path
    )
    data = resolve_data_paths(child_env, root)

    dry = bool(args.dry_run or args.status)
    killed: List[int] = []
    started = False
    served: Optional[str] = None

    if args.status:
        print(
            format_report(
                tip=tip,
                branch=branch,
                app_js_v=app_js_v,
                port=args.port,
                host=args.host,
                orphans=orphans,
                killed=[],
                started=False,
                dry_run=True,
                data=data,
                dropped=dropped,
            )
        )
        return 0

    if orphans:
        killed = kill_pids(orphans, dry_run=dry)
        if not dry:
            time.sleep(1.5)

    if not args.kill_only:
        if dry:
            started = True
        else:
            still = find_listener_pids(args.port)
            if still:
                kill_pids(still, dry_run=False)
                time.sleep(1.0)
            start_serve(
                root, host=args.host, port=args.port, dry_run=False, reload=not args.no_reload, child_env=child_env
            )
            started = True
            if not args.no_wait:
                ok = wait_health(health_check_host(args.host), args.port)
                if ok:
                    served = served_app_js_version(health_check_host(args.host), args.port) or ""
                if not ok:
                    print(
                        format_report(
                            tip=tip,
                            branch=branch,
                            app_js_v=app_js_v,
                            port=args.port,
                            host=args.host,
                            orphans=orphans,
                            killed=killed,
                            started=started,
                            dry_run=dry,
                            data=data,
                            dropped=dropped,
                        )
                    )
                    print("ERROR: serve did not become healthy", file=sys.stderr)
                    return 2

    print(
        format_report(
            tip=tip,
            branch=branch,
            app_js_v=app_js_v,
            port=args.port,
            host=args.host,
            orphans=orphans,
            killed=killed,
            started=started,
            dry_run=dry,
            served=served,
            data=data,
            dropped=dropped,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
