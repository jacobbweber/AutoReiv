"""CARD-532: dedicated live QA environment and one-command journey runs.

The coding assistant runs each card's live-test journeys itself against its own AutoReiv serve with
real models, never Jacob's serve (port 8000) or his live data.

    python scripts/live_qa.py run --journeys card-520,card-530          # throwaway env on :8770, desktop + phone
    python scripts/live_qa.py run --journeys card-530 --data clone       # clone of the real AppData (copy only)
    python scripts/live_qa.py start [--data throwaway|clone] [--port 8770]
    python scripts/live_qa.py stop | status | reset | clone

Data (D1): throwaway by default (``scratch/live_qa_data``, wiped each start); ``--data clone`` copies
``%LOCALAPPDATA%\\AutoReiv`` into it first (never writes back; the vault key is not copied; the copy's
``wiki_path`` / ``data_dir`` settings are pointed at the copy). Paths are vetted with the CARD-467 guard.
Models (REQ-532-008): a throwaway env gets the real vLLM provider (``AUTOREIV_QA_VLLM_URL`` /
``AUTOREIV_QA_MODEL``, default qwen3.8:latest on Nimo Ollama 192.168.1.29:11434). Reports (D2): the journey
runner writes to ``AUTOREIV_QA_REPORT_DIR`` or ``<temp>/autoreiv-qa/<card>`` (a C: path on Jarvis).
Judge (D3): off unless ``--judge``.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Mapping, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smoke_server as guard  # noqa: E402  (CARD-467 data guard, same folder)

CHECKOUT = guard.CHECKOUT
DEFAULT_PORT = 8770
FORBIDDEN_PORTS = frozenset({8000})
DATA_REL = Path("scratch") / "live_qa_data"
PID_FILE_REL = Path("scratch") / "live_qa_serve.pid"
LOG_FILE_REL = Path("scratch") / "live_qa_serve.log"
RUNNER_REL = Path("tests") / "e2e" / "journeys" / "run.mjs"
CLONE_SKIP_NAMES = frozenset({".vault_key"})
CLONE_SKIP_SUFFIXES = (".db-wal", ".db-shm", ".lock")
# 2026-09-29: Nimo Ollama; qwen3.6:35b-a3b-65k is gone and qwen3-coder cannot load next to the pinned models.
DEFAULT_VLLM_URL = "http://192.168.1.29:11434/v1"
DEFAULT_MODEL = "qwen3.8:latest"
# CARD-575/576: Ollama context size for QA calls, the same as Jacob's Developer and Nimo's OLLAMA_CONTEXT_LENGTH
# (full 262144 for qwen3.8), so Nimo keeps one load of the model. AUTOREIV_QA_NUM_CTX overrides; 0 = off.
DEFAULT_NUM_CTX = 262144
EXIT_REFUSED = 2
EXIT_CHECKOUT_CHANGED = 3
EXIT_MODEL_DOWN = 4
MODEL_RETRY_WAIT_S = 30
SANDBOX_DIR_NAME = "autoreiv-qa-checkout"


def validate_port(port: int) -> int:
    port = int(port)
    if port in FORBIDDEN_PORTS:
        raise ValueError(f"Port {port} is Jacob's serve; the live QA env uses its own port (default {DEFAULT_PORT}).")
    return port


def data_dir_for(checkout: Path = CHECKOUT) -> Path:
    return checkout / DATA_REL


def data_problems(data_dir: Path, env: Mapping[str, str], checkout: Path = CHECKOUT) -> list[str]:
    """CARD-467 guard: every resolved path under <checkout>/scratch and none in live AppData."""
    qa_env = guard.build_smoke_env(env, data_dir)
    paths = guard.resolve_paths(qa_env, checkout)
    paths["fake_localappdata"] = Path(qa_env["LOCALAPPDATA"])
    return guard.live_data_problems(paths, guard.live_data_roots(env), required_parent=checkout / "scratch")


def live_appdata(env: Mapping[str, str]) -> Path:
    local = env.get("LOCALAPPDATA")
    return (Path(local) if local else Path.home() / "AppData" / "Local") / "AutoReiv"


def _skip(name: str) -> bool:
    return name in CLONE_SKIP_NAMES or name.endswith(CLONE_SKIP_SUFFIXES)


def clone_appdata(src: Path, dst: Path) -> dict:
    """Copy ``src`` (real AppData) into ``dst``. Read-only on ``src``; SQLite files via the backup API."""
    src, dst = Path(src), Path(dst)
    if not src.is_dir():
        raise FileNotFoundError(f"No AutoReiv data at {src}")
    if guard.is_within(dst, src) or guard.is_within(src, dst):
        raise ValueError(f"Refusing to clone: {dst} and {src} overlap")
    if dst.exists():
        shutil.rmtree(dst)
    copied, skipped = 0, []
    for root, dirs, files in os.walk(src):
        rel = Path(root).relative_to(src)
        (dst / rel).mkdir(parents=True, exist_ok=True)
        for name in files:
            if _skip(name):
                skipped.append(str(rel / name))
                continue
            s, d = Path(root) / name, dst / rel / name
            if name.endswith(".db"):
                _sqlite_copy(s, d)
            else:
                shutil.copy2(s, d)
            copied += 1
    repointed = repoint_settings(dst / "database" / "autoreiv.db", dst)
    return {"copied": copied, "skipped": skipped, "repointed": repointed}


def _sqlite_copy(src: Path, dst: Path) -> None:
    source = sqlite3.connect(f"file:{src.as_posix()}?mode=ro", uri=True)
    try:
        target = sqlite3.connect(str(dst))
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()


def repoint_settings(db_path: Path, data_dir: Path) -> list[str]:
    """Point the copy's ``wiki_path`` / ``data_dir`` settings into the copy so nothing writes to live data."""
    if not Path(db_path).is_file():
        return []
    wanted = {"wiki_path": str(Path(data_dir) / "wiki"), "data_dir": str(data_dir)}
    changed = []
    conn = sqlite3.connect(str(db_path))
    try:
        have = {r[0] for r in conn.execute("SELECT key FROM settings WHERE key IN ('wiki_path','data_dir')")}
        for key in sorted(have):
            conn.execute("UPDATE settings SET value_json = ? WHERE key = ?", (json.dumps(wanted[key]), key))
            changed.append(key)
        conn.commit()
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()
    return changed


def model_target(env: Mapping[str, str]) -> tuple[str, str]:
    url = (env.get("AUTOREIV_QA_VLLM_URL") or DEFAULT_VLLM_URL).strip().rstrip("/")
    return url, (env.get("AUTOREIV_QA_MODEL") or DEFAULT_MODEL).strip()


def is_ollama_url(url: str) -> bool:
    return ":11434" in (url or "")


def qa_num_ctx(env: Mapping[str, str]) -> int:
    """CARD-575: num_ctx for QA calls to an Ollama host; AUTOREIV_QA_NUM_CTX overrides, 0 turns it off."""
    raw = str(env.get("AUTOREIV_QA_NUM_CTX") or "").strip()
    if not raw:
        return DEFAULT_NUM_CTX
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_NUM_CTX


def check_model(url: str, model: str, timeout: float = 600.0, num_ctx: int = 0) -> bool:
    """True when the QA model answers a 5-token chat completion.

    CARD-575: on an Ollama host with num_ctx set, use the native /api/chat so options.num_ctx is honoured
    (the /v1 endpoint loads the model at the server default context).
    CARD-592: 600 s (was 20 s): the ping may queue behind other chats or wait for a model load.
    """
    if num_ctx and is_ollama_url(url):
        host = url.rstrip("/").removesuffix("/v1")
        payload = {"model": model, "messages": [{"role": "user", "content": "ping"}], "stream": False,
                   "options": {"num_ctx": int(num_ctx), "num_predict": 5}}
        endpoint, answered = f"{host}/api/chat", lambda d: bool(d.get("message"))
    else:
        payload = {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5}
        endpoint, answered = f"{url}/chat/completions", lambda d: bool(d.get("choices"))
    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status == 200 and answered(json.loads(res.read() or b"{}"))
    except (urllib.error.URLError, OSError, ValueError):
        return False


def model_ok(env: Mapping[str, str]) -> bool:
    url, model = model_target(env)
    ok = check_model(url, model, num_ctx=qa_num_ctx(env))
    print(f"[live-qa] model {model} at {url}: {'ok' if ok else 'model endpoint down'}")
    return ok


def provider_payload(env: Mapping[str, str]) -> dict:
    """POST /api/settings/providers body that points a throwaway env at the real vLLM."""
    url = (env.get("AUTOREIV_QA_VLLM_URL") or DEFAULT_VLLM_URL).strip()
    model = (env.get("AUTOREIV_QA_MODEL") or DEFAULT_MODEL).strip()
    if ":11434" in url:  # CARD-562: an Ollama host (e.g. Nimo) is registered as the ollama provider, not vLLM
        host = url.rstrip("/").removesuffix("/v1")
        return {"provider_id": "ollama", "default_provider_id": "ollama", "base_url": host, "ollama_host": host, "default_model_id": model}
    return {"provider_id": "vllm", "default_provider_id": "vllm", "base_url": url, "openai_base_url": url, "default_model_id": model}


def context_matrix(env: Mapping[str, str], matrix: Optional[dict]) -> Optional[dict]:
    """CARD-575: POST /api/settings/matrix body so the throwaway serve asks Ollama for the QA num_ctx.

    Keeps the rest of the current matrix; sets default_context_window and the model's entry in
    model_context_windows. None when the QA target is not an Ollama host or num_ctx is off.
    """
    url, model = model_target(env)
    n = qa_num_ctx(env)
    if not n or not is_ollama_url(url):
        return None
    body = dict(matrix or {})
    windows = dict(body.get("model_context_windows") or {})
    windows[model] = n
    body["model_context_windows"] = windows
    body["default_context_window"] = n
    return body


def list_journeys(journeys_dir: Path = CHECKOUT / RUNNER_REL.parent) -> list[str]:
    """Journey ids (file stems) under tests/e2e/journeys: card-<N>-<name>.mjs."""
    return sorted(p.stem for p in Path(journeys_dir).glob("card-*.mjs"))


def select_journeys(available: list[str], wanted: list[str]) -> list[str]:
    """"card-530" or a full id prefix selects journeys; empty selects all."""
    if not wanted:
        return list(available)
    return [j for j in available if any(j.startswith(w) for w in wanted)]


def plan_runs(journeys: list[str], viewports: list[str]) -> list[tuple[str, str, bool]]:
    """One (journey, viewport, append) per run; each run gets a fresh env, the first starts a new report."""
    plan = [(j, v) for j in journeys for v in viewports]
    return [(j, v, i > 0) for i, (j, v) in enumerate(plan)]


def runner_command(port: int, journeys: list[str], viewports: list[str], out: str = "", attempts: int = 1, judge: bool = False, card: str = "", append: bool = False) -> list[str]:
    cmd = ["node", str(RUNNER_REL), "--base", f"http://127.0.0.1:{port}", "--viewports", ",".join(viewports), "--attempts", str(attempts)]
    if journeys:
        cmd += ["--journeys", ",".join(journeys)]
    if out:
        cmd += ["--out", out]
    if card:
        cmd += ["--card", card]
    if judge:
        cmd.append("--judge")
    if append:
        cmd.append("--append")
    return cmd


# --- CARD-555: the throwaway serve runs from a disposable worktree, never from (or into) the real checkout ---------


def sandbox_checkout_dir(env: Mapping[str, str]) -> Path:
    """Disposable checkout for the serve: AUTOREIV_QA_CHECKOUT_DIR, else <temp>/autoreiv-qa-checkout (outside the repo)."""
    configured = str(env.get("AUTOREIV_QA_CHECKOUT_DIR") or "").strip()
    return Path(configured) if configured else Path(tempfile.gettempdir()) / SANDBOX_DIR_NAME


def checkout_problems(dest: Path, checkout: Path = CHECKOUT) -> list[str]:
    if guard.is_within(dest, checkout) or guard.is_within(checkout, dest):
        return [f"sandbox checkout {dest} overlaps the real checkout {checkout}"]
    return []


def _git(checkout: Path, *args: str, check: bool = True) -> str:
    res = subprocess.run(["git", "-C", str(checkout), *args], capture_output=True, text=True, check=check)
    return (res.stdout or "").strip()


def snapshot_commit(checkout: Path = CHECKOUT) -> str:
    """The working tree's tracked state as a commit (``git stash create``; nothing is stashed), else HEAD."""
    return _git(checkout, "stash", "create") or _git(checkout, "rev-parse", "HEAD")


def _rmtree(path: Path) -> None:
    def onexc(func, p, _exc):
        os.chmod(p, 0o700)
        func(p)

    for _ in range(10):
        if not path.exists():
            return
        try:
            shutil.rmtree(path, onexc=onexc)
        except OSError:
            time.sleep(0.5)


def remove_sandbox_checkout(checkout: Path, dest: Path) -> None:
    dest = Path(dest)
    try:
        _git(checkout, "worktree", "remove", "--force", str(dest), check=False)
    except OSError:
        pass
    _rmtree(dest)
    try:
        _git(checkout, "worktree", "prune", check=False)
    except OSError:
        pass


def prepare_sandbox_checkout(checkout: Path, dest: Path) -> Path:
    """A fresh detached worktree at ``dest`` with the checkout's tracked work (committed and uncommitted)."""
    checkout, dest = Path(checkout), Path(dest)
    problems = checkout_problems(dest, checkout)
    if problems:
        raise ValueError(problems[0])
    remove_sandbox_checkout(checkout, dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    _git(checkout, "worktree", "add", "--detach", str(dest), snapshot_commit(checkout))
    return dest


def serve_launch(port: int, qa_env: Mapping[str, str], sandbox: Path, checkout: Path = CHECKOUT) -> tuple[list[str], str, dict]:
    """Command, cwd and env for the throwaway serve: code, cwd and checkout tools in the sandbox; real checkout protected."""
    env = dict(qa_env)
    env["AUTOREIV_CHECKOUT_ROOT"] = str(sandbox)
    env["PYTHONPATH"] = os.pathsep.join([str(sandbox)] + [p for p in str(qa_env.get("PYTHONPATH") or "").split(os.pathsep) if p])
    env["AUTOREIV_PROTECTED_WRITE_ROOTS"] = str(checkout)
    cmd = [sys.executable, "-m", "uvicorn", "src.web.app:app", "--host", "127.0.0.1", "--port", str(port)]
    return cmd, str(sandbox), env


def git_status(checkout: Path = CHECKOUT) -> str:
    return _git(checkout, "status", "--porcelain=v1", "--untracked-files=all", check=False)


def checkout_changes(before: str, after: str) -> list[str]:
    old = {line for line in before.splitlines() if line.strip()}
    new = {line for line in after.splitlines() if line.strip()}
    return sorted(new - old) + [f"(no longer) {line}" for line in sorted(old - new)]


def report_dir(card: str, out: str, env: Mapping[str, str]) -> Path:
    if out:
        return Path(out)
    root = str(env.get("AUTOREIV_QA_REPORT_DIR") or "").strip() or str(Path(tempfile.gettempdir()) / "autoreiv-qa")
    return Path(root) / card.lower()


def append_checkout_guard(summary_dir: Path, checkout: Path, changed: list[tuple[str, list[str]]]) -> None:
    lines = ["", "## Real checkout guard (CARD-555)", ""]
    if changed:
        lines.append(f"FAIL: the real checkout {checkout} changed during the run (git status):")
        for label, items in changed:
            lines += [f"- {label}: {item}" for item in items]
    else:
        lines.append(f"PASS: git status of the real checkout {checkout} unchanged during the run.")
    summary_dir.mkdir(parents=True, exist_ok=True)
    with open(summary_dir / "summary.md", "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _http(method: str, url: str, body: Optional[dict] = None, timeout: float = 5.0) -> int:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status
    except urllib.error.HTTPError as err:
        return err.code
    except (urllib.error.URLError, OSError):
        return 0


def _get_json(url: str, timeout: float = 10.0) -> Optional[dict]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as res:
            data = json.loads(res.read() or b"{}")
            return data if isinstance(data, dict) else None
    except (urllib.error.URLError, OSError, ValueError):
        return None


def healthy(port: int) -> bool:
    return _http("GET", f"http://127.0.0.1:{port}/api/health") == 200


def stop(port: int = DEFAULT_PORT, checkout: Path = CHECKOUT) -> bool:
    pid_file = checkout / PID_FILE_REL
    stopped = False
    if pid_file.is_file():
        pid = pid_file.read_text().strip()
        if pid.isdigit():
            if os.name == "nt":
                subprocess.call(["taskkill", "/PID", pid, "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.call(["kill", pid])
            stopped = True
        pid_file.unlink(missing_ok=True)
    for _ in range(20):
        if not healthy(port):
            break
        time.sleep(0.5)
    if stopped:
        remove_sandbox_checkout(checkout, sandbox_checkout_dir(os.environ))
    return stopped


def start(port: int = DEFAULT_PORT, mode: str = "throwaway", checkout: Path = CHECKOUT, env: Optional[Mapping[str, str]] = None) -> int:
    port = validate_port(port)
    env = dict(os.environ if env is None else env)
    data_dir = data_dir_for(checkout)
    problems = data_problems(data_dir, env, checkout)
    if problems:
        for msg in problems:
            print(f"[live-qa] REFUSED: {msg}", file=sys.stderr)
        return EXIT_REFUSED
    stop(port, checkout)
    if mode == "clone":
        info = clone_appdata(live_appdata(env), data_dir)
        print(f"[live-qa] cloned real AppData: {info['copied']} files; skipped {info['skipped']}; repointed {info['repointed']}")
    else:
        guard.wipe_smoke_dir(data_dir, checkout)
    qa_env = guard.build_smoke_env(env, data_dir)
    # CARD-555: serve the code from a disposable worktree so repo_file_*, write_project_file and cli_exec default to
    # it; the real checkout is a protected write root for the serve.
    sandbox = prepare_sandbox_checkout(checkout, sandbox_checkout_dir(env))
    cmd, cwd, serve_env = serve_launch(port, qa_env, sandbox, checkout)
    print(f"[live-qa] serving code from sandbox {sandbox} (real checkout protected)")
    log = open(checkout / LOG_FILE_REL, "w", encoding="utf-8")
    flags = (subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008) if os.name == "nt" else 0  # DETACHED_PROCESS
    proc = subprocess.Popen(cmd, env=serve_env, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
    (checkout / PID_FILE_REL).write_text(str(proc.pid))
    for _ in range(120):
        if healthy(port):
            break
        if proc.poll() is not None:
            print(f"[live-qa] serve exited early; see {checkout / LOG_FILE_REL}", file=sys.stderr)
            return 1
        time.sleep(1)
    else:
        print("[live-qa] serve did not become healthy in 120 s", file=sys.stderr)
        return 1
    if mode != "clone":
        status = _http("POST", f"http://127.0.0.1:{port}/api/settings/providers", provider_payload(env), timeout=30)
        print(f"[live-qa] real vLLM provider set: HTTP {status}")
        if status != 200:
            return 1
        current = (_get_json(f"http://127.0.0.1:{port}/api/settings") or {}).get("matrix")
        body = context_matrix(env, current if isinstance(current, dict) else None)
        if body is not None:
            status = _http("POST", f"http://127.0.0.1:{port}/api/settings/matrix", body, timeout=30)
            print(f"[live-qa] Ollama context {body['default_context_window']} set: HTTP {status}")
            if status != 200:
                return 1
    print(f"[live-qa] up on http://127.0.0.1:{port} ({mode}, data {data_dir})")
    return 0


def _parse(argv: Optional[list[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CARD-532 live QA environment and journey runner")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("start", "run"):
        s = sub.add_parser(name)
        s.add_argument("--port", type=int, default=DEFAULT_PORT)
        s.add_argument("--data", choices=("throwaway", "clone"), default="throwaway")
        if name == "run":
            s.add_argument("--journeys", default="")
            s.add_argument("--viewports", default="desktop,phone")
            s.add_argument("--out", default="")
            s.add_argument("--card", default="")
            s.add_argument("--attempts", type=int, default=1, help="reruns allowed only when the model endpoint is down")
            s.add_argument("--judge", action="store_true")
            s.add_argument("--keep", action="store_true", help="leave the env running afterwards")
            s.add_argument("--shared-env", action="store_true", help="one env for all runs (default: a fresh env per journey and viewport)")
    for name in ("stop", "status"):
        sub.add_parser(name).add_argument("--port", type=int, default=DEFAULT_PORT)
    sub.add_parser("reset")
    sub.add_parser("clone")
    sub.add_parser("check-model", help=f"5-token completion against the QA model; exit {EXIT_MODEL_DOWN} if down")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)  # keep [live-qa] lines in order with the node output
    args = _parse(argv)
    if args.cmd == "start":
        return start(args.port, args.data)
    if args.cmd == "stop":
        stop(args.port)
        return 0
    if args.cmd == "status":
        print(f"[live-qa] :{args.port} healthy={healthy(args.port)}")
        return 0
    if args.cmd == "reset":
        stop(DEFAULT_PORT)
        guard.wipe_smoke_dir(data_dir_for(), CHECKOUT)
        print(f"[live-qa] wiped {data_dir_for()}")
        return 0
    if args.cmd == "check-model":
        return 0 if model_ok(os.environ) else EXIT_MODEL_DOWN
    if args.cmd == "clone":
        stop(DEFAULT_PORT)
        print(clone_appdata(live_appdata(os.environ), data_dir_for()))
        return 0
    wanted = [j.strip() for j in args.journeys.split(",") if j.strip()]
    journeys = select_journeys(list_journeys(), wanted)
    viewports = [v.strip() for v in args.viewports.split(",") if v.strip()]
    if not journeys:
        print(f"[live-qa] no journeys match {wanted}", file=sys.stderr)
        return EXIT_REFUSED
    # One report folder for the whole run: --card, else card-<N> for a single journey, else "journeys".
    if not model_ok(os.environ):
        return EXIT_MODEL_DOWN  # a dead model is not a product failure; do not run journeys
    card = args.card or ("-".join(journeys[0].split("-")[:2]) if len(journeys) == 1 else "journeys")
    runs = [(journeys, viewports, False)] if args.shared_env else [([j], [v], a) for j, v, a in plan_runs(journeys, viewports)]
    worst = 0
    baseline = git_status(CHECKOUT)  # CARD-555: the run fails if the real checkout changes
    changed: list[tuple[str, list[str]]] = []
    try:
        for i, (js, vs, append) in enumerate(runs):
            if i == 0 or not args.shared_env:
                rc = start(args.port, args.data)
                if rc:
                    return rc
            cmd = runner_command(args.port, js, vs, args.out, 1, args.judge, card, append=append)
            rc = subprocess.call(cmd, cwd=str(CHECKOUT), shell=(os.name == "nt"))
            # Retry only when the model endpoint failed, never to paper over a product failure.
            tries = 1
            while rc and not model_ok(os.environ):
                if tries >= args.attempts:
                    return EXIT_MODEL_DOWN
                tries += 1
                time.sleep(MODEL_RETRY_WAIT_S)
                rerun = runner_command(args.port, js, vs, args.out, 1, args.judge, card, append=True)
                rc = subprocess.call(rerun, cwd=str(CHECKOUT), shell=(os.name == "nt"))
            worst = max(worst, rc)
            now = git_status(CHECKOUT)
            diff = checkout_changes(baseline, now)
            if diff:
                label = f"{','.join(js)} ({','.join(vs)})"
                print(f"[live-qa] FAIL: the real checkout changed during {label}: {'; '.join(diff)}")
                changed.append((label, diff))
                worst = max(worst, EXIT_CHECKOUT_CHANGED)
                baseline = now
            if not args.shared_env and not (args.keep and i == len(runs) - 1):
                stop(args.port)
        if not changed:
            print(f"[live-qa] real checkout unchanged during the run ({CHECKOUT})")
        append_checkout_guard(report_dir(card, args.out, os.environ), CHECKOUT, changed)
        return worst
    finally:
        if not args.keep:
            stop(args.port)


if __name__ == "__main__":
    sys.exit(main())
