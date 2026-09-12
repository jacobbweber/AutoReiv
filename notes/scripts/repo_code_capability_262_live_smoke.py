"""CARD-262 live smoke — repo/code capability path (Jarvis→Ollama)."""
from __future__ import annotations

import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from src.domain.capabilities.models import (
    CapabilityIndexEntry,
    CapabilityKind,
    RiskLevel,
    TrustTier,
)
from src.infrastructure.memory.repositories.capability_catalog import (
    CapabilityCatalogRepository,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

BASE = "http://127.0.0.1:8000"
DB = Path.home() / "AppData/Local/AutoReiv/database/autoreiv.db"
LIVE_OUT = Path("notes/marathon-card262-live-smoke.json")

POS_PROMPT = (
    "Using repo_file_read, what does AGENTS.md say about cards? "
    "Done-when: answer cites only content returned by repo_file_read of AGENTS.md. "
    "Keep under 120 words."
)
NEG_PROMPT = (
    "Using repo_file_read, what does TotallyFakeCheckoutFile-ZZZ.md say about the three beats? "
    "Done-when: if read fails, honest fail / park - do not invent. Keep under 80 words."
)

PATH_RE = re.compile(
    r"(AGENTS\.md|TotallyFakeCheckoutFile-ZZZ\.md|src/[\w./\-]+|[\w.\-]+\.md)",
    re.IGNORECASE,
)


def tip_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def seed() -> list[str]:
    store = SQLiteStateStore(db_path=str(DB))
    repo = CapabilityCatalogRepository(store)
    ids = []
    for entry in (
        CapabilityIndexEntry(
            id="tool.repo_file_read",
            kind=CapabilityKind.TOOL,
            name="repo_file_read",
            summary="Read a UTF-8 file under the AutoReiv checkout root (sandboxed)",
            keywords=[
                "repo", "checkout", "agents.md", "read", "source", "code",
                "file", "repository", "codebase", "cards",
            ],
            roles=["assistant", "homelab", "general", "developer"],
            trust_tier=TrustTier.TRUSTED,
            risk_level=RiskLevel.LOW,
            requires_hitl=False,
            source="card262_live_smoke",
        ),
        CapabilityIndexEntry(
            id="tool.repo_file_list",
            kind=CapabilityKind.TOOL,
            name="repo_file_list",
            summary="List a directory under the AutoReiv checkout root (sandboxed)",
            keywords=["repo", "checkout", "list", "directory", "files", "source"],
            roles=["assistant", "homelab", "general", "developer"],
            trust_tier=TrustTier.TRUSTED,
            risk_level=RiskLevel.LOW,
            requires_hitl=False,
            source="card262_live_smoke",
        ),
    ):
        repo.upsert_entry(entry)
        ids.append(entry.id)
    return ids


def stream_until_done(client: httpx.Client, prompt: str, *, agent_id: str = "assistant", max_s: float = 300.0) -> dict:
    sid = client.post(
        f"{BASE}/api/sessions",
        json={"agent_id": agent_id, "title": "card262-live"},
        timeout=30.0,
    ).json()["id"]
    events: list[tuple[str, dict]] = []
    turn_tail = ""
    job_id = None
    repo_grounding = None
    t0 = time.time()
    with client.stream(
        "POST",
        f"{BASE}/api/chat/stream",
        json={
            "session_id": sid,
            "content": prompt,
            "agent_id": agent_id,
            "approval_mode": "ask",
        },
        timeout=max_s + 30,
    ) as resp:
        resp.raise_for_status()
        buf = ""
        done = False
        for chunk in resp.iter_text():
            buf += chunk
            while "\n\n" in buf:
                block, buf = buf.split("\n\n", 1)
                ev = None
                data_lines: list[str] = []
                for line in block.splitlines():
                    if line.startswith("event:"):
                        ev = line[6:].strip()
                    elif line.startswith("data:"):
                        data_lines.append(line[5:].strip())
                if not ev:
                    continue
                try:
                    payload = json.loads("\n".join(data_lines) or "{}")
                except Exception:
                    payload = {"raw": data_lines}
                if not isinstance(payload, dict):
                    payload = {"value": payload}
                events.append((ev, payload))
                if ev == "job_created":
                    job_id = payload.get("job_id") or job_id
                if ev == "repo_grounding":
                    repo_grounding = payload
                if ev == "token":
                    turn_tail += str(payload.get("text") or "")
                if ev == "turn_done":
                    turn_tail = str(payload.get("content") or turn_tail)
                    done = True
                if ev == "error":
                    turn_tail += " ERROR:" + json.dumps(payload)[:400]
                    done = True
            if done:
                break
            if time.time() - t0 > max_s:
                break

    # Soft-approve write parks if any (should be none for read-only)
    try:
        ar = client.get(f"{BASE}/api/chat/approvals/{sid}", timeout=15.0)
        items = ar.json() if ar.status_code == 200 else []
        if isinstance(items, dict):
            items = items.get("approvals") or []
        for item in items or []:
            aid = item.get("approval_id") or item.get("id")
            if not aid:
                continue
            client.post(
                f"{BASE}/api/chat/approve",
                json={"approval_id": aid, "session_id": sid, "decision": "approve"},
                timeout=30.0,
            )
    except Exception:
        pass

    provenanced: list[str] = []
    tool_reads = 0
    tool_fails = 0
    for ev, p in events:
        if ev in {"tool_output", "tool_end", "tool_result"}:
            raw = str(p.get("result") or p.get("output") or p.get("content") or "")
            name = str(p.get("name") or p.get("tool_name") or "")
            try:
                data = json.loads(raw) if raw.strip().startswith("{") else p
            except Exception:
                data = p
            if isinstance(data, dict):
                if data.get("success") is True and data.get("path"):
                    provenanced.append(str(data["path"]).replace("\\", "/"))
                    tool_reads += 1
                if data.get("success") is False:
                    tool_fails += 1
            if "repo_file_read" in name.lower() or "repo_file_read" in raw:
                tool_reads += 1
        if ev == "repo_honest_fail":
            tool_fails += 1

    lower = turn_tail.lower()
    honest = (
        "not done" in lower
        or "will not invent" in lower
        or "honest" in lower
        or "file not found" in lower
        or "repo_honest_fail" in [e for e, _ in events]
        or any(e == "repo_honest_fail" for e, _ in events)
    )
    grounded_cards = (
        "card" in lower
        and ("ready" in lower or "three beats" in lower or "build" in lower or "agents.md" in lower)
    )

    return {
        "session_id": sid,
        "job_id": job_id,
        "agent_id": agent_id,
        "event_names": [e for e, _ in events],
        "repo_grounding": repo_grounding,
        "turn_tail": turn_tail[:1200],
        "provenanced_paths": sorted(set(provenanced)),
        "tool_reads": tool_reads,
        "tool_fails": tool_fails,
        "honest_fail_signal": honest,
        "grounded_cards_signal": grounded_cards,
        "elapsed_s": round(time.time() - t0, 1),
    }


def main() -> int:
    matched = seed()
    health = httpx.get(f"{BASE}/api/health", timeout=10.0).json()
    with httpx.Client(timeout=60.0) as client:
        pos = stream_until_done(client, POS_PROMPT, agent_id="assistant")
        neg = stream_until_done(client, NEG_PROMPT, agent_id="assistant")

    pos_ok = bool(
        pos.get("job_id")
        and (
            pos.get("tool_reads", 0) > 0
            or "AGENTS.md" in (pos.get("provenanced_paths") or [])
            or (
                pos.get("grounded_cards_signal")
                and "not done" not in (pos.get("turn_tail") or "").lower()
            )
        )
        and "invent" not in (pos.get("turn_tail") or "").lower()
    )
    # Positive also OK if repo_grounding fired and answer references cards from read
    if not pos_ok and pos.get("repo_grounding") and pos.get("grounded_cards_signal"):
        pos_ok = True
    if pos.get("tool_reads", 0) > 0 and pos.get("grounded_cards_signal"):
        pos_ok = True

    neg_ok = bool(
        neg.get("honest_fail_signal")
        or "not done" in (neg.get("turn_tail") or "").lower()
        or "will not invent" in (neg.get("turn_tail") or "").lower()
        or "file not found" in (neg.get("turn_tail") or "").lower()
    )
    # Negative must NOT invent three-beats content as if read succeeded
    tail_l = (neg.get("turn_tail") or "").lower()
    # Invent = claims file contents about three beats without honest-fail / Not done.
    invent_three = (
        ("three beats" in tail_l or "beat 1" in tail_l)
        and "not done" not in tail_l
        and "will not invent" not in tail_l
        and "does not appear" not in tail_l
        and "file not found" not in tail_l
        and "honest fail" not in tail_l
        and neg.get("tool_reads", 0) == 0
        and not neg.get("honest_fail_signal")
    )
    if invent_three:
        neg_ok = False
    # Prefer explicit honest-fail rewrite / missing-file admission
    if (
        "not done" in tail_l
        or "will not invent" in tail_l
        or "checkout read missing" in tail_l
        or "does not appear" in tail_l
        or "file not found" in tail_l
        or any(e == "repo_honest_fail" for e in (neg.get("event_names") or []))
    ):
        neg_ok = True

    artifact = {
        "card": "CARD-262",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tip_sha": tip_sha(),
        "serve": BASE,
        "matched_at_seed": matched,
        "health": health,
        "scenarios": {
            "positive_agents_md_cards": {
                "prompt": POS_PROMPT,
                "result": pos,
                "pass": pos_ok,
            },
            "negative_missing_file_no_invent": {
                "prompt": NEG_PROMPT,
                "result": neg,
                "pass": neg_ok,
            },
        },
        "pass": bool(pos_ok and neg_ok),
        "design_room_one_liner": (
            "Homelab-class checkout reads via catalog repo_file_*; Jobs claim only "
            "tool-provenanced paths — failed/missing read honest-fails, never invents."
        ),
    }
    LIVE_OUT.parent.mkdir(parents=True, exist_ok=True)
    LIVE_OUT.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": artifact["pass"], "pos": pos_ok, "neg": neg_ok,
                      "pos_job": pos.get("job_id"), "neg_job": neg.get("job_id"),
                      "tip": artifact["tip_sha"]}, indent=2))
    return 0 if artifact["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
