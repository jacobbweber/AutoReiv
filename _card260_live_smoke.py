"""CARD-260 live smoke v2 — exit on turn_done; no resume for need-sources."""
from __future__ import annotations

import json
import re
import subprocess
import time
import uuid
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
LIVE_OUT = Path("notes/marathon-card260-live-smoke.json")
PATH_RE = re.compile(
    r"((?:00_Inbox|01_Notes|02_Resources|notes|inbox|resources)(?:/[\w.\-]+)+\.md)",
    re.IGNORECASE,
)

EMPTY_PROMPT = (
    "Write a short Wiki note in 00_Inbox about Zorblax-9 quantum flute maintenance "
    "(obscure topic with no vault notes). Done-when: I can open that note via "
    "wiki_note_read. Keep it under 80 words."
)
EXISTING_PROMPT = (
    "Write a short Wiki note in 00_Inbox summarizing standing Jobs in AutoReiv "
    "using only matched wiki notes. Done-when: I can open that note via wiki_note_read. "
    "Keep it under 120 words."
)
SOURCE_DEP_PROMPT = (
    "Summarize what the wiki says about Zorblax-9 quantum flute maintenance "
    "using only matched wiki notes. Done-when: sources are cited via wiki_note_read."
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
            id="tool.wiki_note_create",
            kind=CapabilityKind.TOOL,
            name="wiki_note_create",
            summary="Create a wiki note in the vault",
            keywords=["wiki", "create", "note", "write", "author", "inbox", "00_inbox"],
            roles=["assistant", "librarian", "general"],
            trust_tier=TrustTier.TRUSTED,
            risk_level=RiskLevel.HIGH,
            requires_hitl=True,
            source="card260_live_smoke",
        ),
        CapabilityIndexEntry(
            id="tool.wiki_note_read",
            kind=CapabilityKind.TOOL,
            name="wiki_note_read",
            summary="Read a wiki note",
            keywords=["wiki", "note", "read", "open", "exists", "inbox"],
            roles=["assistant", "librarian", "general"],
            trust_tier=TrustTier.TRUSTED,
            risk_level=RiskLevel.LOW,
            requires_hitl=False,
            source="card260_live_smoke",
        ),
        CapabilityIndexEntry(
            id="tool.wiki_note_search",
            kind=CapabilityKind.TOOL,
            name="wiki_note_search",
            summary="Search wiki notes",
            keywords=["wiki", "search", "notes", "inventory", "matched"],
            roles=["assistant", "librarian", "general"],
            trust_tier=TrustTier.TRUSTED,
            risk_level=RiskLevel.LOW,
            requires_hitl=False,
            source="card260_live_smoke",
        ),
    ):
        repo.upsert_entry(entry)
        ids.append(entry.id)
    return ids


def stream_until_done(client: httpx.Client, prompt: str, *, max_s: float = 240.0) -> dict:
    sid = client.post(
        f"{BASE}/api/sessions",
        json={"agent_id": "assistant", "title": "card260-v2"},
        timeout=30.0,
    ).json()["id"]
    events: list[tuple[str, dict]] = []
    turn_tail = ""
    job_id = None
    wiki_grounding = None
    t0 = time.time()
    with client.stream(
        "POST",
        f"{BASE}/api/chat/stream",
        json={
            "session_id": sid,
            "content": prompt,
            "agent_id": "assistant",
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
                if ev == "wiki_grounding":
                    wiki_grounding = payload
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

    # Approve once if parked on create (existing scenario), then optional short resume
    need_sources = bool(
        (wiki_grounding or {}).get("need_sources")
        or "need sources" in turn_tail.lower()
    )
    if not need_sources:
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

    claimed = [m.group(1).replace("\\", "/") for m in PATH_RE.finditer(turn_tail)]
    claimed = [c for c in claimed if "..." not in c]
    # Provenance from tool events + vault grounding allow-list
    provenanced: list[str] = []
    wg = wiki_grounding or {}
    for pth in list(wg.get("hit_paths") or []) + list(wg.get("matched_read_paths") or []):
        if pth:
            provenanced.append(str(pth).replace("\", "/"))
    for ev, p in events:
        if ev == "tool_output":
            raw = str(p.get("result") or "")
            for m in PATH_RE.finditer(raw):
                provenanced.append(m.group(1).replace("\\", "/"))
            try:
                data = json.loads(raw)
                if isinstance(data, dict) and data.get("path"):
                    provenanced.append(str(data["path"]).replace("\\", "/"))
            except Exception:
                pass
    allowed = {x.lower() for x in provenanced}
    ungrounded = [c for c in claimed if c.lower() not in allowed]

    return {
        "session_id": sid,
        "job_id": job_id,
        "event_names": [e for e, _ in events],
        "wiki_grounding": wiki_grounding,
        "need_sources": need_sources,
        "waiting_approval": any(
            e == "turn_done" and p.get("waiting_approval") for e, p in events
        )
        or "waiting_approval" in turn_tail
        or "park" in turn_tail.lower(),
        "turn_tail": turn_tail[-1500:],
        "claimed_paths": claimed,
        "provenanced_paths": sorted(set(provenanced)),
        "ungrounded_claims": ungrounded,
        "elapsed_s": round(time.time() - t0, 2),
    }


def main() -> None:
    matched = seed()
    health = httpx.get(f"{BASE}/api/health", timeout=15.0).json()
    client = httpx.Client(timeout=300.0)

    print("scenario source_dep...", flush=True)
    source = stream_until_done(client, SOURCE_DEP_PROMPT, max_s=90)
    source_ok = (
        (source.get("wiki_grounding") or {}).get("action") == "need_sources_park"
        or source.get("need_sources")
        or source.get("waiting_approval")
    ) and not source.get("ungrounded_claims")
    print("source", source_ok, (source.get("wiki_grounding") or {}).get("action"), source.get("job_id"), flush=True)

    print("scenario empty_create...", flush=True)
    empty = stream_until_done(client, EMPTY_PROMPT, max_s=420)
    empty_action = (empty.get("wiki_grounding") or {}).get("action")
    empty_ok = (
        empty_action in {"grounded_only", "need_sources_park"}
        or empty.get("need_sources")
        or empty.get("waiting_approval")
        or (bool(empty.get("provenanced_paths")) and not empty.get("ungrounded_claims"))
    ) and not empty.get("ungrounded_claims")
    print("empty", empty_ok, empty_action, empty.get("job_id"), flush=True)

    print("scenario existing...", flush=True)
    existing = stream_until_done(client, EXISTING_PROMPT, max_s=420)
    existing_action = (existing.get("wiki_grounding") or {}).get("action")
    existing_ok = (
        existing_action in {"proceed_with_hits", "grounded_only"}
        or existing.get("waiting_approval")
        or bool(existing.get("job_id"))
    ) and not existing.get("ungrounded_claims")
    print("existing", existing_ok, existing_action, existing.get("job_id"), flush=True)

    artifact = {
        "card": "CARD-260",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tip_sha": tip_sha(),
        "serve": BASE,
        "matched_at_seed": matched,
        "health": health,
        "scenarios": {
            "source_dependent_thin": {
                "prompt": SOURCE_DEP_PROMPT,
                "result": source,
                "pass": bool(source_ok),
                "done_bar": "source-dependent thin -> HITL park need sources",
            },
            "empty_thin_create": {
                "prompt": EMPTY_PROMPT,
                "result": empty,
                "pass": bool(empty_ok),
                "done_bar": "empty/thin -> park need sources OR grounded_only; no hallucinated path",
            },
            "existing_matched_notes": {
                "prompt": EXISTING_PROMPT,
                "result": existing,
                "pass": bool(existing_ok),
                "done_bar": "topic with existing matched notes may proceed grounded; no ungrounded claims",
            },
        },
        "pass": bool(source_ok and empty_ok and existing_ok),
        "job_ids": {
            "source_dep": source.get("job_id"),
            "empty": empty.get("job_id"),
            "existing": existing.get("job_id"),
        },
        "ungrounded_any": bool(
            source.get("ungrounded_claims")
            or empty.get("ungrounded_claims")
            or existing.get("ungrounded_claims")
        ),
        "done_bar_proof": "Chat never claims a note path that wasn't wiki_note_create/read'd",
    }
    LIVE_OUT.parent.mkdir(parents=True, exist_ok=True)
    LIVE_OUT.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(json.dumps({"pass": artifact["pass"], "job_ids": artifact["job_ids"]}, indent=2), flush=True)
    if not artifact["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
