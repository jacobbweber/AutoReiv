"""Promote phase: HITL gate — holds until approved, then pack write happens in API (CARD-171)."""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.application.agent_training_factory.phase import PhaseContext, PhaseResult
from src.application.agent_training_factory.registry import PHASE_PROMOTE
from src.domain.orchestration.factory_packets import FactoryPacket


def check_tool_collisions(
    target_agent_id: str,
    proposed_tools: List[str],
    data_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Inspect target pack and disk inventory for duplicate or colliding callable names [REQ-FACT-054]."""
    clean_target = (target_agent_id or "").strip()
    tool_counts = Counter(proposed_tools)
    duplicate_declarations = [name for name, count in tool_counts.items() if count > 1]

    unique_proposed = list(tool_counts.keys())
    target_pack_conflicts: List[str] = []
    cross_pack_conflicts: Dict[str, str] = {}

    # Discover packs directories
    candidate_pack_roots: List[Path] = []
    if data_dir:
        candidate_pack_roots.append(Path(data_dir) / "packs")
        candidate_pack_roots.append(Path(data_dir))
    else:
        candidate_pack_roots.append(Path("./data/packs"))
        candidate_pack_roots.append(Path("packs"))
        if os.environ.get("AUTOREIV_DATA_DIR"):
            candidate_pack_roots.append(Path(os.environ["AUTOREIV_DATA_DIR"]) / "packs")
        if os.environ.get("LOCALAPPDATA"):
            candidate_pack_roots.append(Path(os.environ["LOCALAPPDATA"]) / "AutoReiv" / "packs")

    for root in candidate_pack_roots:
        if not root.is_dir():
            continue
        target_dir = root / clean_target

        if target_dir.is_dir():
            pack_json = target_dir / "pack.json"
            if pack_json.is_file():
                try:
                    data = json.loads(pack_json.read_text(encoding="utf-8"))
                    existing_tools = set(data.get("pack_tool_names") or []) | set(data.get("allowed_tool_names") or [])
                    for t in unique_proposed:
                        if t in existing_tools and t not in target_pack_conflicts:
                            target_pack_conflicts.append(t)
                except Exception:
                    pass
            tools_dir = target_dir / "tools"
            if tools_dir.is_dir():
                for py_file in tools_dir.glob("*.py"):
                    if py_file.stem != "__init__" and py_file.stem in unique_proposed:
                        if py_file.stem not in target_pack_conflicts:
                            target_pack_conflicts.append(py_file.stem)

        for sibling_dir in root.iterdir():
            if not sibling_dir.is_dir() or sibling_dir.name == clean_target:
                continue
            sibling_tools = set()
            sib_pack_json = sibling_dir / "pack.json"
            if sib_pack_json.is_file():
                try:
                    sib_data = json.loads(sib_pack_json.read_text(encoding="utf-8"))
                    sibling_tools.update(sib_data.get("pack_tool_names") or [])
                    sibling_tools.update(sib_data.get("allowed_tool_names") or [])
                except Exception:
                    pass
            sib_tools_dir = sibling_dir / "tools"
            if sib_tools_dir.is_dir():
                for py_file in sib_tools_dir.glob("*.py"):
                    if py_file.stem != "__init__":
                        sibling_tools.add(py_file.stem)
            for t in unique_proposed:
                if t in sibling_tools and t not in cross_pack_conflicts:
                    cross_pack_conflicts[t] = sibling_dir.name

    all_conflicts = list(dict.fromkeys(duplicate_declarations + target_pack_conflicts + list(cross_pack_conflicts.keys())))
    has_collision = len(all_conflicts) > 0

    return {
        "has_collision": has_collision,
        "conflicts": all_conflicts,
        "duplicate_declarations": duplicate_declarations,
        "target_pack_conflicts": target_pack_conflicts,
        "cross_pack_conflicts": cross_pack_conflicts,
    }


class PromotePhase:
    id = PHASE_PROMOTE
    label = "Promote"

    async def run(self, ctx: PhaseContext) -> PhaseResult:
        job = ctx.job
        # Enter waiting_approval; actual pack write is performed by the promote API
        # after human approval (HITL), keeping surfaces working.
        # Check if this job delivers an MCP server [CARD-185]
        is_mcp = getattr(job, "deliverable_type", "") == "mcp"
        proposed_tools: List[str] = []
        if ctx.repo:
            for p in ctx.repo.list_packets(job.id) or []:
                payload = getattr(p, "payload", None) or {}
                if isinstance(payload, dict):
                    if not is_mcp and payload.get("deliverable_type") == "mcp":
                        is_mcp = True
                    files = payload.get("files_map") or {}
                    if "mcp/server.py" in files:
                        is_mcp = True
                    if payload.get("tool_names") and isinstance(payload["tool_names"], list):
                        proposed_tools.extend([str(x) for x in payload["tool_names"]])
                    elif payload.get("tool_name"):
                        proposed_tools.append(str(payload["tool_name"]))
                    for f in files:
                        norm = str(f).replace("\\", "/")
                        if norm.startswith("tools/") and norm.endswith(".py"):
                            proposed_tools.append(Path(norm).stem)

        unique_tools = [t for t in proposed_tools if t and t != "procedural_skills"]
        collisions = check_tool_collisions(
            target_agent_id=job.target_agent_id,
            proposed_tools=unique_tools,
            data_dir=getattr(ctx, "data_dir", None),
        )


        rebuild_hint = (
            f" If using Docker, rebuild: docker build -t autoreiv-{job.target_agent_id}-mcp:latest packs/{job.target_agent_id}/mcp"
            if is_mcp
            else ""
        )
        packet = FactoryPacket(
            job_id=job.id,
            packet_type="promote",
            sender_role="promote",
            recipient_role="hitl",
            node_id=PHASE_PROMOTE,
            payload={
                "message": (
                    f"Promote gate: waiting for human approval to deploy "
                    f"{job.target_agent_id} to packs/.{rebuild_hint}"
                ),
                "phase": PHASE_PROMOTE,
                "awaiting": "hitl_approval",
                "container_build_cmd": (
                    f"docker build -t autoreiv-{job.target_agent_id}-mcp:latest packs/{job.target_agent_id}/mcp"
                    if is_mcp
                    else None
                ),
                "proposed_tools": list(dict.fromkeys(unique_tools)),
                "collisions": collisions,
                "has_collision": collisions.get("has_collision", False),
            },
        )

        ctx.repo.save_packet(packet)
        return PhaseResult(
            outcome="ok",
            message=packet.payload["message"],
            waiting=True,
            artifacts={"collisions": collisions},
        )

