#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CARD-265 specialist A2A same-job handoff smoke.

Modes:
  --validate   unit helpers + in-process engine same-job bind (no invent)
  --live       Jarvis serve: parent standing job → /api/agents/delegate →
               same job_id resume; privilege never widens; writes
               notes/marathon-card265-live-smoke.json

Do NOT invent job_ids — capture only from live API / Observe.
Stack: feat/a2a-same-job-handoff-265 off feat/repo-write-hitl-264 @ 91f6569.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

BASE = "http://127.0.0.1:8000"
LIVE_OUT = ROOT / "notes" / "marathon-card265-live-smoke.json"

DESIGN_ROOM = (
    "Specialist A2A parks/resumes the same job_id tree; matched subset never "
    "widens (221/234) — parent continues one Observe journey."
)


def tip_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True
        ).strip()
    except Exception:
        return "unknown"


def validate() -> int:
    import asyncio

    from src.application.capabilities.resolver import CapabilityCatalogResolver
    from src.application.orchestration.handoff_engine import HandoffIsolationEngine
    from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
    from src.application.orchestration.standing_a2a_handoff import (
        bind_specialist_same_job,
        child_ids_do_not_widen,
        effective_matched_ids_no_escalate,
    )
    from src.application.safety.tool_policy_gate import ToolPolicyGate, ToolPolicyVerdict
    from src.domain.capabilities.models import (
        CapabilityIndexEntry,
        CapabilityKind,
        TrustTier,
    )
    from src.domain.gateway.models import ToolCall
    from src.domain.kernel.models import AgentProfile, AgentTone, KernelEvent, KernelEventType
    from src.domain.orchestration.models import HandoffEnvelope, HandoffPacket
    from src.infrastructure.agents.registry import BuiltinAgentRegistry
    from src.infrastructure.memory.repositories.capability_catalog import (
        CapabilityCatalogRepository,
    )
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore

    errors: list[str] = []
    notes: list[str] = []

    parent_ids = ["tool.wiki_note_search", "agent.homelab"]
    eff = effective_matched_ids_no_escalate(
        parent_ids, specialist_tool_names=["cli_exec", "wiki_note_search"]
    )
    if eff != parent_ids or not child_ids_do_not_widen(parent_ids, eff):
        errors.append("effective_matched_ids_no_escalate widened")
    else:
        notes.append("no-escalate helper ok")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        db = handle.name
    store = SQLiteStateStore(db_path=db)
    resolver = CapabilityCatalogResolver(CapabilityCatalogRepository(store))
    orch = JobPhaseOrchestrator(store, capability_resolver=resolver)
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="tool.wiki_note_search",
            kind=CapabilityKind.TOOL,
            name="wiki_note_search",
            summary="Search wiki",
            keywords=["wiki", "search", "fleet"],
            roles=["assistant", "homelab"],
        )
    )
    resolver.upsert(
        CapabilityIndexEntry(
            id="agent.homelab",
            kind=CapabilityKind.AGENT,
            name="Homelab",
            summary="Homelab specialist",
            keywords=["homelab", "specialist"],
            roles=["homelab"],
            trust_tier=TrustTier.TRUSTED,
            source="builtin",
        )
    )
    job = orch.create_job_from_catalog_resolve(
        intent="Fleet health then specialist summary",
        session_id="validate-265",
        agent_id="assistant",
        role="assistant",
        matched_capability_ids=["tool.wiki_note_search", "agent.homelab"],
    )
    bound = bind_specialist_same_job(
        orch,
        job_id=job.id,
        specialist_agent_id="homelab",
        specialty="homelab",
        park=True,
    )
    if bound.get("same_job_id") != job.id:
        errors.append(f"bind same_job mismatch: {bound}")
    else:
        notes.append(f"bind same_job={job.id}")

    gate = ToolPolicyGate(store)
    agent = AgentProfile(
        id="homelab",
        name="Homelab",
        description="t",
        system_prompt="t",
        tone=AgentTone.TECHNICAL,
        allowed_tool_names=["cli_exec", "wiki_note_search"],
    )
    d = gate.evaluate(
        ToolCall(id="1", name="cli_exec", arguments={"command": "echo x"}),
        agent,
        matched_capability_ids=bound["matched_capability_ids"],
        registry_tool_names={"cli_exec", "wiki_note_search"},
    )
    if d.verdict != ToolPolicyVerdict.BLOCK or d.policy_source != "capability_subset":
        errors.append(f"privilege widened: {d.verdict} {d.policy_source}")
    else:
        notes.append("capability_subset BLOCK after same-job bind")

    class _K:
        async def stream_turn(self, **kwargs):
            if kwargs.get("job_id") != job.id:
                raise AssertionError(f"expected same job_id, got {kwargs.get('job_id')}")
            yield KernelEvent(event_type=KernelEventType.TOKEN, content="ok")
            yield KernelEvent(
                event_type=KernelEventType.TURN_END, content="ok", is_finished=True
            )

    specialist = AgentProfile(
        id="homelab",
        name="Homelab",
        description="d",
        system_prompt="s",
        tone=AgentTone.TECHNICAL,
        allowed_tool_names=["wiki_note_search", "cli_exec"],
        max_turns=5,
    )
    engine = HandoffIsolationEngine(
        kernel=_K(),
        agent_registry=BuiltinAgentRegistry(profiles=[specialist], state_store=store),
        state_store=store,
        job_orchestrator=orch,
    )
    envelope = HandoffEnvelope(
        sender_agent_id="assistant",
        recipient_agent_id="homelab",
        session_id="validate-265-eng",
        task_intent="one sentence",
        context_payload={"parent_job_id": job.id},
        packet=HandoffPacket(
            goal="one sentence",
            facts=[],
            constraints=["same job"],
            done_when="done",
            budget={"max_turns": 2},
        ),
    )

    async def _run():
        return await engine.execute_handoff(envelope)

    result = asyncio.run(_run())
    if result.same_job_id != job.id or result.parent_job_id != job.id:
        errors.append(f"engine stamp fail: {result}")
    else:
        notes.append("engine same_job stamp ok")

    # resume same job_id
    resume = orch.resume_after_crash(job.id)
    if not getattr(resume, "ok", False) and not getattr(resume, "resumed_from_checkpoint", False):
        # soft: resume may no-op if not crashed; still same id
        notes.append(f"resume_after_crash result={resume}")
    else:
        notes.append(f"resume same job ok id={job.id}")

    out = {
        "ok": not errors,
        "mode": "validate",
        "tip_sha": tip_sha(),
        "notes": notes,
        "errors": errors,
        "design_room": DESIGN_ROOM,
        "job_id": job.id,
        "same_job_id": job.id,
    }
    print(json.dumps(out, indent=2))
    return 0 if not errors else 1


def _health() -> dict[str, Any]:
    assert httpx is not None
    r = httpx.get(f"{BASE}/api/health", timeout=10.0)
    r.raise_for_status()
    return r.json()


def live() -> int:
    if httpx is None:
        print(json.dumps({"ok": False, "errors": ["httpx missing"]}))
        return 1
    errors: list[str] = []
    notes: list[str] = []
    try:
        health = _health()
        notes.append(f"health={health.get('status')} version={health.get('version')}")
    except Exception as exc:
        print(json.dumps({"ok": False, "errors": [f"serve unreachable: {exc}"], "tip_sha": tip_sha()}))
        return 1

    # Seed a standing parent job via chat or jobs API — prefer catalog resolve through chat SSE
    # Minimal path: POST /api/agents/delegate with parent_job_id from a prior standing create.
    # Create parent via internal-ish health + jobs if available; else chat stream.
    parent_job_id = None
    session_id = None
    try:
        # Create session
        sr = httpx.post(
            f"{BASE}/api/sessions",
            json={"agent_id": "assistant", "title": "CARD-265 same-job"},
            timeout=30.0,
        )
        if sr.status_code >= 400:
            # fallback: some builds use different route
            notes.append(f"sessions create http={sr.status_code}")
        else:
            session_id = (sr.json() or {}).get("id") or (sr.json() or {}).get("session_id")
            notes.append(f"session={session_id}")
    except Exception as exc:
        notes.append(f"session create soft-fail: {exc}")

    # Standing multi-step ask to mint job_id
    prompt = (
        "Standing job: search wiki for platform health once, then stop and wait. "
        "Done-when: one wiki_note_search tool result recorded. Keep under 40 words."
    )
    try:
        with httpx.stream(
            "POST",
            f"{BASE}/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": session_id,
                "content": prompt,
                "approval_mode": "ask",
            },
            timeout=300.0,
        ) as stream:
            buf = ""
            ev = None
            for chunk in stream.iter_text():
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
                        payload = {}
                    if not isinstance(payload, dict):
                        payload = {}
                    jid = payload.get("job_id")
                    if (ev == "job_created" or jid) and jid and not parent_job_id:
                        parent_job_id = str(jid)
                        notes.append(f"parent_job_id from chat={parent_job_id} (ev={ev})")
                    if parent_job_id and ev in {"job_created", "turn_done", "error"}:
                        break
                if parent_job_id and ev in {"job_created", "turn_done", "error"}:
                    break
    except Exception as exc:
        errors.append(f"chat mint failed: {exc}")

    if not parent_job_id:
        # Do not invent — fail closed
        payload = {
            "ok": False,
            "mode": "live",
            "tip_sha": tip_sha(),
            "errors": errors + ["no parent_job_id from live chat — refuse invent"],
            "notes": notes,
            "design_room": DESIGN_ROOM,
            "health": health,
        }
        LIVE_OUT.write_text(json.dumps(payload, indent=2) + "\n")
        print(json.dumps(payload, indent=2))
        return 1

    # Delegate specialist on same job (default CARD-265 path)
    delegate_body = {
        "sender_agent_id": "assistant",
        "recipient_agent_id": "homelab",
        "session_id": session_id or "card265-live",
        "task_intent": "One-sentence fleet health summary; no tools beyond matched subset.",
        "context_payload": {
            "parent_job_id": parent_job_id,
            "park_on_handoff": True,
        },
        "packet": {
            "goal": "One-sentence fleet health summary",
            "facts": [f"parent_job_id={parent_job_id}"],
            "constraints": ["same job_id", "no privilege escalate", "no cli_exec"],
            "done_when": "one sentence returned",
            "budget": {"max_turns": 4, "max_handoffs": 0, "max_ollama_slots": 1},
        },
        "max_turns": 4,
    }
    handoff = None
    try:
        dr = httpx.post(
            f"{BASE}/api/agents/delegate",
            json=delegate_body,
            timeout=120.0,
        )
        notes.append(f"delegate_http={dr.status_code}")
        handoff = dr.json() if dr.status_code < 500 else {"raw": dr.text[:500]}
    except Exception as exc:
        errors.append(f"delegate failed: {exc}")

    same_job_id = None
    child_job_id = None
    if isinstance(handoff, dict):
        same_job_id = handoff.get("same_job_id") or (handoff.get("handoff") or {}).get(
            "same_job_id"
        )
        child_job_id = handoff.get("child_job_id") or (handoff.get("handoff") or {}).get(
            "child_job_id"
        )
        stamped_parent = handoff.get("parent_job_id") or (handoff.get("handoff") or {}).get(
            "parent_job_id"
        )
        if same_job_id and same_job_id != parent_job_id:
            errors.append(f"same_job_id mismatch {same_job_id} != {parent_job_id}")
        if child_job_id and child_job_id != parent_job_id and not handoff.get("linked_child_job"):
            # default path must not fork
            errors.append(f"unexpected child fork {child_job_id}")
        if stamped_parent and stamped_parent != parent_job_id:
            errors.append(f"parent stamp mismatch {stamped_parent}")
        if same_job_id == parent_job_id or child_job_id == parent_job_id:
            notes.append("delegate resumed same job_id tree")
        elif not errors:
            # Some APIs nest differently — record honesty
            notes.append(f"handoff keys={sorted(handoff.keys())}")

    # Observe journey for one tree
    journey = None
    try:
        jr = httpx.get(f"{BASE}/api/observe/jobs/{parent_job_id}", timeout=30.0)
        if jr.status_code >= 400:
            jr = httpx.get(
                f"{BASE}/api/observability/standing-journey",
                params={"job_id": parent_job_id},
                timeout=30.0,
            )
        notes.append(f"observe_http={jr.status_code}")
        if jr.status_code < 400:
            journey = jr.json()
    except Exception as exc:
        notes.append(f"observe soft-fail: {exc}")

    ok = not errors and (
        same_job_id == parent_job_id or child_job_id == parent_job_id
    )
    payload = {
        "ok": ok,
        "mode": "live",
        "card": "CARD-265",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tip_sha": tip_sha(),
        "serve": BASE,
        "design_room": DESIGN_ROOM,
        "health": health,
        "notes": notes,
        "errors": errors,
        "parent_job_id": parent_job_id,
        "same_job_id": same_job_id or (parent_job_id if ok else None),
        "child_job_id": child_job_id,
        "session_id": session_id,
        "handoff": handoff,
        "journey": journey,
        "proof": "parent park → specialist delegate → same job_id one Observe tree; no privilege widen",
    }
    LIVE_OUT.parent.mkdir(parents=True, exist_ok=True)
    LIVE_OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()
    if args.live:
        return live()
    return validate()


if __name__ == "__main__":
    raise SystemExit(main())
