"""Restart AutoReiv serve with orphan hygiene [CARD-256].

Find listener(s) on a port (default 8000), optionally kill them, start one fresh
serve from the current branch tip, and print tip SHA + app.js?v= from index.html.

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
from typing import Iterable, List, Optional, Sequence

APP_JS_VERSION_RE = re.compile(
    r"""['\"]/static/app\.js\?v=([^'\"]+)['\"]""",
    re.IGNORECASE,
)
DEFAULT_PORT = 8000
DEFAULT_HOST = "127.0.0.1"
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
        # Windows: Proto LocalAddress ForeignAddress State PID
        # Proto may be TCP / TCPV6
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
    """Force-kill PIDs. Returns list actually targeted."""
    killed: List[int] = []
    for pid in pids:
        if dry_run:
            killed.append(pid)
            continue
        if sys.platform.startswith("win"):
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                check=False,
                capture_output=True,
            )
        else:
            subprocess.run(["kill", "-TERM", str(pid)], check=False, capture_output=True)
        killed.append(pid)
    return killed


def start_serve(
    root: Path,
    *,
    host: str,
    port: int,
    dry_run: bool = False,
    log_path: Optional[Path] = None,
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
    if dry_run:
        return None
    log_path = log_path or (root / ".autoreiv-restart-serve.log")
    log_f = open(log_path, "a", encoding="utf-8")
    creation = 0
    child_env = os.environ.copy()
    try:
        from src.application.orchestration.phase_llm_resilience import load_repo_dotenv

        load_repo_dotenv(root)
        child_env = os.environ.copy()
    except Exception:
        pass
    kwargs = {
        "cwd": str(root),
        "stdout": log_f,
        "stderr": subprocess.STDOUT,
        "env": child_env,
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
        f"verify=Ctrl+F5 then confirm Network shows app.js?v={app_js_v}",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="CARD-256 serve/orphan hygiene restart helper")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--dry-run", action="store_true", help="Report only; do not kill or start")
    p.add_argument("--kill-only", action="store_true", help="Kill orphans; do not start serve")
    p.add_argument("--status", action="store_true", help="Print tip/version/listeners; no mutate")
    p.add_argument("--no-wait", action="store_true", help="Do not wait for /api/health after start")
    p.add_argument("--root", type=Path, default=None, help="Repo root override")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    root = Path(args.root).resolve() if args.root else repo_root()
    tip = tip_sha(root)
    branch = tip_branch(root)
    app_js_v = read_app_js_version(root)
    orphans = find_listener_pids(args.port)

    dry = bool(args.dry_run or args.status)
    killed: List[int] = []
    started = False

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
            )
        )
        return 0

    if orphans:
        killed = kill_pids(orphans, dry_run=dry)
        if not dry:
            time.sleep(1.5)

    if not args.kill_only:
        if dry:
            started = True  # would start
        else:
            still = find_listener_pids(args.port)
            if still:
                kill_pids(still, dry_run=False)
                time.sleep(1.0)
            start_serve(root, host=args.host, port=args.port, dry_run=False)
            started = True
            if not args.no_wait:
                ok = wait_health(args.host, args.port)
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
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
