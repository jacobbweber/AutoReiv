"""Author phase: LLM + Wiki grounding (+ synthesizer seed) -> SKILL.md + tool code (CARD-171)."""

from __future__ import annotations

import ast
import json
import logging
from typing import Any, Dict, List

from src.application.agent_training_factory.llm import phase_llm_json
from src.application.agent_training_factory.phase import PhaseContext, PhaseResult
from src.application.agent_training_factory.phases.blueprint import (
    hyperv_focus_from_brief,
    hyperv_lifecycle_blueprint,
    wants_hyperv_multi_skill,
)
from src.application.agent_training_factory.prompt_registry import get_phase_system_prompt
from src.application.agent_training_factory.registry import PHASE_AUTHOR, PHASE_BLUEPRINT, PHASE_VERIFY
from src.application.agent_training_factory.wiki_frontmatter import filter_factory_notes
from src.application.orchestration.tool_synthesizer import ToolSynthesizer
from src.domain.orchestration.factory_packets import FactoryPacket

logger = logging.getLogger(__name__)

_STUB_PATTERNS = (
    "agent for managing",
    "managing tasks",
)



def _latest_verify_failure_notes(ctx: PhaseContext) -> str:
    """Surface the last Verify critic_notes so Author can adapt (not blind retry)."""
    try:
        packets = ctx.repo.list_packets(ctx.job_id)
    except Exception:
        return ""
    for p in reversed(packets or []):
        role = getattr(p, "sender_role", "") or ""
        node = getattr(p, "node_id", "") or ""
        payload = getattr(p, "payload", None) or {}
        if role not in ("verify", "scenario_verify", "sandbox_runner") and node not in (
            PHASE_VERIFY,
            "scenario_verify",
            "sandbox_battery_node",
        ):
            continue
        if payload.get("passed") is True:
            continue
        notes = str(payload.get("critic_notes") or "").strip()
        if notes:
            return notes
        msg = str(payload.get("message") or "").strip()
        if msg:
            return msg
    return ""


class AuthorPhase:
    id = PHASE_AUTHOR
    label = "Author"

    async def run(self, ctx: PhaseContext) -> PhaseResult:
        job = ctx.job
        clean_slug = job.target_agent_id.replace("-", "_").lower()
        objectives = list(ctx.objectives)

        blueprint = _latest_blueprint(ctx)
        # Narrow Hyper-V trains: never author unattend/template bleed from a stale wide blueprint.
        if wants_hyperv_multi_skill(job.target_agent_id, job.seed_intent, objectives):
            focuses = hyperv_focus_from_brief(job.target_agent_id, job.seed_intent, objectives)
            # Belt-and-suspenders: checkpoint-only briefs never keep networking/unattend.
            combined_raw = f"{job.seed_intent} {' '.join(map(str, objectives))}".lower()
            if "checkpoint" in focuses and (
                "no switch" in combined_raw
                or "no nic" in combined_raw
                or "no network" in combined_raw
                or "no networking" in combined_raw
                or "no virtual switch" in combined_raw
                or "checkpoint cmdlets only" in combined_raw
                or "checkpoints only" in combined_raw
            ):
                focuses = {"checkpoint"}
            focused = hyperv_lifecycle_blueprint(
                job.target_agent_id, job.seed_intent, objectives, focuses=focuses
            )
            blueprint = {
                **(blueprint or {}),
                "skills": focused.get("skills") or [],
                "tools": focused.get("tools") or [],
                "scenarios": (blueprint or {}).get("scenarios") or focused.get("scenarios") or [],
                "focuses": sorted(focuses),
                "rationale": focused.get("rationale") or (blueprint or {}).get("rationale"),
            }
        tool_specs = list((blueprint or {}).get("tools") or [])
        skill_specs = list((blueprint or {}).get("skills") or [])
        deliverable_type = (blueprint or {}).get("deliverable_type") or getattr(job, "deliverable_type", "")
        if not deliverable_type and ctx.repo:
            for p in ctx.repo.list_packets(job.id) or []:
                payload = getattr(p, "payload", None) or {}
                if isinstance(payload, dict) and payload.get("deliverable_type"):
                    deliverable_type = payload["deliverable_type"]
                    break
        if not deliverable_type:
            deliverable_type = "native_tool"


        if deliverable_type == "skill":
            tool_specs = []
            if not skill_specs:
                skill_specs = [
                    {
                        "id": clean_slug,
                        "name": f"{job.target_agent_id.replace('-', ' ').title()} Skill",
                        "description": job.seed_intent[:200],
                        "tools": [],
                    }
                ]
        else:
            if not tool_specs:
                tool_specs = [{"name": f"manage_{clean_slug}", "skill_id": clean_slug}]
            if not skill_specs:
                skill_specs = [
                    {
                        "id": clean_slug,
                        "name": f"{job.target_agent_id} Skill",
                        "tools": [tool_specs[0].get("name") or f"manage_{clean_slug}"],
                    }
                ]

        # Map tool -> skill_id from blueprint
        tool_to_skill: Dict[str, str] = {}
        for sk in skill_specs:
            sid = sk.get("id") or clean_slug
            for tn in sk.get("tools") or []:
                tool_to_skill[str(tn)] = str(sid)
        for t in tool_specs:
            tn = str(t.get("name") or "")
            if tn and tn not in tool_to_skill:
                tool_to_skill[tn] = str(t.get("skill_id") or clean_slug)

        wiki_slice = _wiki_slice(ctx)
        manifest = {}
        if job.environment_manifest_json:
            try:
                manifest = json.loads(job.environment_manifest_json)
            except Exception:
                pass

        last_fail = _latest_verify_failure_notes(ctx)
        fail_block = (
            f"LAST VERIFY / SCENARIO FAILURE (adapt - do not blind-retry the same mistake):\n{last_fail[:2000]}\n\n"
            if last_fail
            else ""
        )

        files_map: Dict[str, str] = {}
        authored_tool_names: List[str] = []
        author_notes: List[str] = []

        # Fast path: Hyper-V multi-skill blueprints already have durable synthesizer seeds.
        # Skipping per-tool LLM avoids 4x90s hangs and docstring escape regressions (CARD-171).
        use_seed_only = len(tool_specs) >= 3 and any(
            str(t.get("name") or "").startswith("manage_hyperv_") for t in tool_specs
        )

        # Author every blueprint tool/skill (multi-skill packs must not collapse to tools[0]).
        if deliverable_type == "skill":
            for sk in skill_specs:
                sid = sk.get("id") or clean_slug
                sname = sk.get("name") or sid.replace("-", " ").title()
                sdesc = sk.get("description") or ""
                skill_md = _format_standard_skill_runbook(
                    skill_id=sid,
                    skill_name=sname,
                    skill_description=sdesc,
                    seed_intent=job.seed_intent,
                    objectives=objectives,
                    agent_id=job.target_agent_id,
                    tool_names=[],
                    body="",
                )
                files_map[f"skills/{sid}/SKILL.md"] = skill_md
            authored_tool_names = []
        else:
            for tool_spec in tool_specs:
                tool_name = tool_spec.get("name") or f"manage_{clean_slug}"
                skill_id = tool_to_skill.get(tool_name) or tool_spec.get("skill_id") or clean_slug
                matched_skill = next((s for s in skill_specs if s.get("id") == skill_id), None)
                skill_name = (matched_skill.get("name") if matched_skill else None) or tool_spec.get("skill_name") or skill_id.replace("-", " ").title()
                skill_desc = (matched_skill.get("description") if matched_skill else None) or tool_spec.get("description") or ""

                focus_objectives = list(tool_spec.get("actions") or []) + list(objectives)
                seed_files = ToolSynthesizer.synthesize_tool(
                    agent_id=job.target_agent_id,
                    seed_intent=job.seed_intent,
                    objectives=focus_objectives or objectives,
                    tool_name=tool_name,
                    skill_id=skill_id,
                )
                seed_tool = seed_files.get(f"tools/{tool_name}.py", "")
                seed_skill = (
                    seed_files.get(f"skills/{skill_id}/SKILL.md")
                    or seed_files.get(f"skills/{clean_slug}/SKILL.md")
                    or ""
                )

                if use_seed_only:
                    llm_data = {"tool_code": seed_tool, "skill_md": seed_skill, "notes": "seed-only-multi-skill"}
                else:
                    system_prompt = get_phase_system_prompt(self.id, ctx.db_path)
                    llm_data = await phase_llm_json(
                        ctx.gateway,
                        system=system_prompt,
                        user=(
                            f"Agent: {job.target_agent_id}\n"
                            f"Tool name: {tool_name}\n"
                            f"Skill id: {skill_id}\n"
                            f"Intent: {job.seed_intent}\n"
                            f"Objectives: {json.dumps(objectives)}\n"
                            f"Manifest: {json.dumps(manifest)[:1500]}\n"
                            f"Blueprint tool: {json.dumps(tool_spec)[:800]}\n"
                            f"Wiki:\n{wiki_slice[:2000]}\n\n"
                            f"{fail_block}"
                            f"SEED TOOL CODE:\n{seed_tool[:3000]}\n\n"
                            f"SEED SKILL.md:\n{seed_skill[:1600]}\n"
                        ),
                        fallback={"tool_code": seed_tool, "skill_md": seed_skill, "notes": "seed"},
                        max_tokens=3500,
                        timeout=90.0,
                    )

                tool_code = str(llm_data.get("tool_code") or seed_tool)
                skill_md = str(llm_data.get("skill_md") or seed_skill)
                # Force focus filter on Hyper-V python tools (strip forbidden action branches).
                if str(tool_name).startswith("manage_hyperv_"):
                    try:
                        from src.application.orchestration.hyperv_tool_builders import _filter_source_to_focus

                        focus = ToolSynthesizer._hyperv_tool_focus(
                            tool_name, job.seed_intent, focus_objectives or objectives
                        )
                        if "FOCUS =" in tool_code or "def " + tool_name in tool_code:
                            tool_code = _filter_source_to_focus(tool_code, focus)
                    except Exception as filt_exc:
                        logger.warning("Author focus filter failed for %s: %s", tool_name, filt_exc)
                # Reject non-importable LLM tool code (e.g. docstring Windows path escapes).
                try:
                    ast.parse(tool_code)
                except SyntaxError as syn_exc:
                    logger.warning("Author LLM tool_code SyntaxError for %s: %s; using seed", tool_name, syn_exc)
                    tool_code = seed_tool or tool_code
                if len(tool_code.strip()) < 40:
                    tool_code = seed_tool
                if len(skill_md.strip()) < 40:
                    skill_md = seed_skill

                domain_bleed = _tool_mismatches_domain(
                    tool_code, job.seed_intent, objectives, job.target_agent_id
                ) or _skill_mismatches_domain(skill_md, job.seed_intent, objectives, job.target_agent_id)
                if _is_stub_skill(skill_md, job.seed_intent, objectives, skill_id=skill_id) or domain_bleed:
                    if domain_bleed:
                        logger.warning("Author output mismatched domain for %s; restoring seed", tool_name)
                    else:
                        logger.warning("Author skill failed quality gate for %s; restoring seed", tool_name)
                    skill_md = _format_standard_skill_runbook(
                        skill_id=skill_id,
                        skill_name=skill_name,
                        skill_description=skill_desc,
                        seed_intent=job.seed_intent,
                        objectives=focus_objectives or objectives,
                        agent_id=job.target_agent_id,
                        tool_names=[tool_name],
                        body=seed_skill or skill_md,
                    )
                    tool_code = seed_tool or tool_code
                else:
                    skill_md = _format_standard_skill_runbook(
                        skill_id=skill_id,
                        skill_name=skill_name,
                        skill_description=skill_desc,
                        seed_intent=job.seed_intent,
                        objectives=focus_objectives or objectives,
                        agent_id=job.target_agent_id,
                        tool_names=[tool_name],
                        body=skill_md,
                    )
                    if not _tool_covers_intent(tool_code, job.seed_intent):
                        tool_code = seed_tool or tool_code

                files_map[f"tools/{tool_name}.py"] = tool_code
                # Keep companion .ps1 from synthesizer when present
                ps1_key = f"tools/{tool_name}.ps1"
                if ps1_key in seed_files:
                    files_map.setdefault(ps1_key, seed_files[ps1_key])
                files_map[f"skills/{skill_id}/SKILL.md"] = skill_md
                for k, v in seed_files.items():
                    files_map.setdefault(k, v)
                authored_tool_names.append(tool_name)
                if llm_data.get("notes"):
                    author_notes.append(str(llm_data.get("notes")))

            for sk in skill_specs:
                sid = sk.get("id") or clean_slug
                sk_key = f"skills/{sid}/SKILL.md"
                if sk_key not in files_map:
                    files_map[sk_key] = _format_standard_skill_runbook(
                        skill_id=sid,
                        skill_name=sk.get("name") or sid.replace("-", " ").title(),
                        skill_description=sk.get("description") or "",
                        seed_intent=job.seed_intent,
                        objectives=objectives,
                        agent_id=job.target_agent_id,
                        tool_names=sk.get("tools") or [],
                        body="",
                    )


        # Check if deliverable architecture is MCP (CARD-176, ADR 0049)
        if deliverable_type == "mcp":

            files_map["mcp/server.py"] = _scaffold_mcp_server(job.target_agent_id, tool_specs, files_map)
            files_map["mcp/Dockerfile"] = _scaffold_mcp_dockerfile(job.target_agent_id)
            files_map["mcp/docker-compose.yml"] = _scaffold_mcp_compose(job.target_agent_id)
            files_map["mcp/requirements.txt"] = _scaffold_mcp_requirements(job.target_agent_id)
            files_map["mcp/run.ps1"] = _scaffold_mcp_run_ps1(job.target_agent_id)
            files_map["mcp/run.sh"] = _scaffold_mcp_run_sh(job.target_agent_id)
            files_map["mcp/README.md"] = _scaffold_mcp_readme(
                job.target_agent_id,
                authored_tool_names or [t.get("name") for t in tool_specs if t.get("name")],
            )

        # Prune files_map to blueprint-scoped tools/skills/mcp only (no setdefault bleed).
        allowed_prefixes = {"mcp/"}
        for tn in authored_tool_names:
            allowed_prefixes.add(f"tools/{tn}.")
        for sk in skill_specs:
            sid = sk.get("id") or clean_slug
            allowed_prefixes.add(f"skills/{sid}/")
        files_map = {
            k: v
            for k, v in files_map.items()
            if any(k.startswith(p) or k.startswith(p.rstrip(".")) for p in allowed_prefixes)
            or any(k == f"tools/{tn}.py" or k == f"tools/{tn}.ps1" for tn in authored_tool_names)
            or any(k == f"skills/{(sk.get('id') or clean_slug)}/SKILL.md" for sk in skill_specs)
            or k.startswith("mcp/")
        }

        # Hyper-V: final focus prune — never keep networking tools on a checkpoint brief.
        if wants_hyperv_multi_skill(job.target_agent_id, job.seed_intent, objectives):
            focuses = hyperv_focus_from_brief(job.target_agent_id, job.seed_intent, objectives)
            allow_frags = set()
            if "checkpoint" in focuses or "vm" in focuses:
                allow_frags.update({"manage_hyperv_vm", "hyperv-vm-lifecycle", "manage_hyperv."})
            if "network" in focuses:
                allow_frags.update({"manage_hyperv_network", "hyperv-networking"})
            if "unattend" in focuses:
                allow_frags.update({"manage_hyperv_unattend", "hyperv-unattend"})
            if "template" in focuses:
                allow_frags.update({"manage_hyperv_template", "hyperv-template"})
            allow_frags.add("mcp/")
            if allow_frags:
                files_map = {
                    k: v
                    for k, v in files_map.items()
                    if any(frag in k.replace("\\", "/") for frag in allow_frags)
                }
                authored_tool_names = [
                    tn for tn in authored_tool_names if any(frag in tn for frag in allow_frags)
                ]

        # Strict deliverable constraint: When deliverable is MCP, strictly omit loose tools/ [CARD-184]
        if deliverable_type == "mcp":
            files_map = {
                k: v
                for k, v in files_map.items()
                if not k.startswith("tools/") and "/tools/" not in k.replace("\\", "/")
            }
        elif deliverable_type == "skill":
            files_map = {
                k: v
                for k, v in files_map.items()
                if not k.startswith("tools/")
                and "/tools/" not in k.replace("\\", "/")
                and not k.startswith("mcp/")
                and "/mcp/" not in k.replace("\\", "/")
            }
            authored_tool_names = []

        primary_tool = (
            "procedural_skills"
            if deliverable_type == "skill"
            else (authored_tool_names[0] if authored_tool_names else f"manage_{clean_slug}")
        )
        packet = FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="author",
            recipient_role="verify",
            node_id=PHASE_AUTHOR,
            payload={
                "message": (
                    f"Author produced {len(authored_tool_names)} tool(s) and "
                    f"{len([k for k in files_map if k.endswith('SKILL.md')])} skill(s) "
                    f"for {job.target_agent_id}."
                ),
                "tool_name": primary_tool,
                "tool_names": authored_tool_names,
                "deliverable_type": deliverable_type,
                "blueprint_skills": skill_specs,
                "authored_files": list(files_map.keys()),
                "files_map": files_map,
                "phase": PHASE_AUTHOR,
                "author_notes": " | ".join(author_notes),
            },
        )

        ctx.repo.save_packet(packet)
        return PhaseResult(
            outcome="ok",
            message=packet.payload["message"],
            artifacts={
                "files_map": files_map,
                "tool_name": primary_tool,
                "tool_names": authored_tool_names,
            },
        )


def _scaffold_mcp_dockerfile(agent_id: str) -> str:
    return """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true
COPY . .
EXPOSE 8080
ENV PORT=8080
CMD ["python", "server.py", "--mode", "http", "--port", "8080"]
"""


def _scaffold_mcp_compose(agent_id: str) -> str:
    clean_slug = agent_id.replace("-", "_").lower()
    return f"""version: '3.8'
services:
  {clean_slug}-mcp:
    build: .
    container_name: {clean_slug}-mcp-server
    ports:
      - "8080:8080"
    environment:
      - PORT=8080
    restart: unless-stopped
"""


def _scaffold_mcp_requirements(agent_id: str) -> str:
    return f"""# Standalone Model Context Protocol Server for {agent_id}
# Zero external mandatory dependencies (uses Python standard library)
"""


def _scaffold_mcp_run_ps1(agent_id: str) -> str:
    return f"""# Run {agent_id} MCP Server on Windows host
param(
    [int]$Port = 8080,
    [string]$Host = "0.0.0.0"
)

Write-Host "Starting {agent_id} MCP server on $Host:$Port..."
python server.py --mode http --host $Host --port $Port
"""


def _scaffold_mcp_run_sh(agent_id: str) -> str:
    return f"""#!/bin/sh
PORT="${{PORT:-8080}}"
HOST="${{HOST:-0.0.0.0}}"
echo "Starting {agent_id} MCP server on $HOST:$PORT..."
exec python3 server.py --mode http --host "$HOST" --port "$PORT"
"""


def _scaffold_mcp_readme(agent_id: str, tool_names: list[str]) -> str:
    title = agent_id.replace("-", " ").title()
    clean_slug = agent_id.replace("-", "_").lower()
    tool_items = "\n".join(f"- `{t}`" for t in tool_names)
    return f"""# {title} Model Context Protocol (MCP) Server

Standalone JSON-RPC 2.0 remote capability service for AutoReiv.

## Available Tools
{tool_items}

## Running with Docker
```bash
docker-compose up --build
```
Or with plain Docker:
```bash
docker build -t {clean_slug}-mcp-server .
docker run -d -p 8080:8080 --name {clean_slug}-mcp-server {clean_slug}-mcp-server
```

## Running on Windows Host (PowerShell)
```powershell
.\\run.ps1 -Port 8080
```

## Running on Linux Host (Bash)
```bash
chmod +x ./run.sh
./run.sh
```

## AutoReiv Agent Configuration
In AutoReiv **Agent Studio** -> **Forge**, under **Per-Agent MCP Servers**:
- **Transport**: `Remote SSE`
- **URL**: `http://<HOST-IP>:8080/sse`
- Click **Probe / Test Connection** to verify connection and tools discovery.
"""


def _scaffold_mcp_server(agent_id: str, tool_specs: list, files_map: dict) -> str:
    clean_slug = agent_id.replace("-", "_").lower()
    is_hyperv = "hyperv" in clean_slug or any("hyperv" in str(ts.get("name", "")).lower() for ts in tool_specs)

    server_lines = [
        '"""',
        f"MCP Server for {agent_id} [CARD-176, CARD-184, REQ-DELIV-003, REQ-DELIV-005].",
        "Standalone dual-mode JSON-RPC 2.0 stdio & HTTP/SSE server (zero external dependencies).",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "import argparse",
        "import asyncio",
        "import inspect",
        "import json",
        "import logging",
        "import os",
        "import subprocess",
        "import sys",
        "import traceback",
        "from http.server import HTTPServer, BaseHTTPRequestHandler",
        "from socketserver import ThreadingMixIn",
        "from typing import Any, Callable, Dict, List, Optional, get_type_hints",
        "",
        "logger = logging.getLogger(__name__)",
        "",
        "",
        "def _python_type_to_json_schema(py_type: Any) -> Dict[str, Any]:",
        '    if py_type in (int, float):',
        '        return {"type": "number" if py_type is float else "integer"}',
        '    if py_type is bool:',
        '        return {"type": "boolean"}',
        '    if py_type is str:',
        '        return {"type": "string"}',
        '    if py_type in (list, List):',
        '        return {"type": "array"}',
        '    if py_type in (dict, Dict):',
        '        return {"type": "object"}',
        '    return {"type": "string"}',
        "",
        "",
        "def derive_input_schema(fn: Callable[..., Any]) -> Dict[str, Any]:",
        '    """Derive JSON schema from callable signature and type annotations."""',
        '    sig = inspect.signature(fn)',
        '    hints = {}',
        '    try:',
        '        hints = get_type_hints(fn)',
        '    except Exception:',
        '        pass',
        '    properties: Dict[str, Any] = {}',
        '    required: List[str] = []',
        '    for name, param in sig.parameters.items():',
        '        if name in ("self", "cls"):',
        '            continue',
        '        py_type = hints.get(name, str)',
        '        schema = _python_type_to_json_schema(py_type)',
        '        if param.default is inspect.Parameter.empty:',
        '            required.append(name)',
        '        else:',
        '            schema["default"] = param.default',
        '        properties[name] = schema',
        '    return {"type": "object", "properties": properties, "required": required}',
        "",
        "",
        "class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):",
        '    daemon_threads = True',
        "",
        "",
        "class PackMCPServer:",
        '    """Lightweight, zero-dependency MCP server supporting stdio and HTTP/SSE JSON-RPC 2.0."""',
        "",
        '    def __init__(self, name: str, version: str = "1.0.0", protocol_version: str = "2024-11-05"):',
        '        self.name = name',
        '        self.version = version',
        '        self.protocol_version = protocol_version',
        '        self._tools: Dict[str, Dict[str, Any]] = {}',
        "",
        '    def tool(',
        '        self,',
        '        name: Optional[str] = None,',
        '        description: str = "",',
        '        input_schema: Optional[Dict[str, Any]] = None,',
        '    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:',
        '        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:',
        '            tool_name = name or fn.__name__',
        '            desc = description or (inspect.getdoc(fn) or f"Tool {tool_name}").split("\\n\\n")[0].strip()',
        '            schema = input_schema or derive_input_schema(fn)',
        '            self.register_tool(name=tool_name, handler=fn, description=desc, input_schema=schema)',
        '            return fn',
        '        return decorator',
        "",
        '    def register_tool(',
        '        self,',
        '        name: str,',
        '        handler: Callable[..., Any],',
        '        description: str = "",',
        '        input_schema: Optional[Dict[str, Any]] = None,',
        '    ) -> None:',
        '        schema = input_schema or derive_input_schema(handler)',
        '        self._tools[name] = {',
        '            "name": name,',
        '            "description": description or f"Tool {name}",',
        '            "inputSchema": schema,',
        '            "handler": handler,',
        '        }',
        "",
        '    def list_tool_definitions(self) -> List[Dict[str, Any]]:',
        '        return [',
        '            {"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]}',
        '            for t in self._tools.values()',
        '        ]',
        "",
        '    async def handle_request_async(self, req: Dict[str, Any]) -> Dict[str, Any]:',
        '        req_id = req.get("id")',
        '        method = req.get("method")',
        '        params = req.get("params") or {}',
        '        if not method or not isinstance(method, str):',
        '            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32600, "message": "Invalid Request: missing method"}}',
        "",
        '        if method == "initialize":',
        '            return {',
        '                "jsonrpc": "2.0",',
        '                "id": req_id,',
        '                "result": {',
        '                    "protocolVersion": self.protocol_version,',
        '                    "capabilities": {"tools": {}},',
        '                    "serverInfo": {"name": self.name, "version": self.version},',
        '                },',
        '            }',
        '        if method in ("notifications/initialized", "initialized"):',
        '            return {}',
        '        if method == "ping":',
        '            return {"jsonrpc": "2.0", "id": req_id, "result": {}}',
        '        if method == "tools/list":',
        '            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.list_tool_definitions()}}',
        '        if method == "tools/call":',
        '            tool_name = params.get("name")',
        '            arguments = params.get("arguments") or {}',
        '            if tool_name not in self._tools:',
        '                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Tool \'{tool_name}\' not found"}}',
        '            handler = self._tools[tool_name]["handler"]',
        '            try:',
        '                if inspect.iscoroutinefunction(handler):',
        '                    output = await handler(**arguments)',
        '                else:',
        '                    output = handler(**arguments)',
        '                if isinstance(output, str):',
        '                    text_content = output',
        '                else:',
        '                    try:',
        '                        text_content = json.dumps(output, indent=2)',
        '                    except Exception:',
        '                        text_content = str(output)',
        '                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": text_content}]}}',
        '            except Exception as e:',
        '                err_msg = f"{type(e).__name__}: {str(e)}"',
        '                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": err_msg}], "isError": True}}',
        "",
        '        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method \'{method}\' not found"}}',
        "",
        '    def handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:',
        '        return asyncio.run(self.handle_request_async(req))',
        "",
        '    def run_stdio(self) -> None:',
        '        if hasattr(sys.stdin, "reconfigure"):',
        '            sys.stdin.reconfigure(encoding="utf-8", line_buffering=True)',
        '        if hasattr(sys.stdout, "reconfigure"):',
        '            sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)',
        '        while True:',
        '            try:',
        '                line = sys.stdin.readline()',
        '                if not line:',
        '                    break',
        '                line = line.strip()',
        '                if not line:',
        '                    continue',
        '                req = json.loads(line)',
        '                resp = self.handle_request(req)',
        '                if resp:',
        '                    sys.stdout.write(json.dumps(resp) + "\\n")',
        '                    sys.stdout.flush()',
        '            except KeyboardInterrupt:',
        '                break',
        '            except Exception as e:',
        '                sys.stderr.write(f"PackMCPServer Error: {e}\\n")',
        '                sys.stderr.flush()',
        "",
        '    def run_http(self, host: str = "0.0.0.0", port: int = 8080) -> None:',
        '        server_inst = self',
        '        class MCPRequestHandler(BaseHTTPRequestHandler):',
        '            def log_message(self, format, *args):',
        '                pass',
        '            def do_GET(self):',
        '                if self.path in ("/", "/health", "/ping"):',
        '                    body = json.dumps({"status": "ok", "server": server_inst.name, "version": server_inst.version, "tools": len(server_inst._tools)}).encode("utf-8")',
        '                    self.send_response(200)',
        '                    self.send_header("Content-Type", "application/json")',
        '                    self.send_header("Content-Length", str(len(body)))',
        '                    self.end_headers()',
        '                    self.wfile.write(body)',
        '                elif self.path in ("/sse", "/mcp"):',
        '                    self.send_response(200)',
        '                    self.send_header("Content-Type", "text/event-stream")',
        '                    self.send_header("Cache-Control", "no-cache")',
        '                    self.send_header("Connection", "keep-alive")',
        '                    self.end_headers()',
        '                    msg = f\'data: {json.dumps({"type": "endpoint", "url": "/mcp"})}\\n\\n\'.encode("utf-8")',
        '                    self.wfile.write(msg)',
        '                else:',
        '                    self.send_response(404)',
        '                    self.end_headers()',
        '            def do_POST(self):',
        '                content_length = int(self.headers.get("Content-Length", 0))',
        '                body = self.rfile.read(content_length)',
        '                try:',
        '                    req = json.loads(body.decode("utf-8"))',
        '                    resp = server_inst.handle_request(req)',
        '                    resp_bytes = json.dumps(resp).encode("utf-8")',
        '                    self.send_response(200)',
        '                    self.send_header("Content-Type", "application/json")',
        '                    self.send_header("Content-Length", str(len(resp_bytes)))',
        '                    self.end_headers()',
        '                    self.wfile.write(resp_bytes)',
        '                except Exception as e:',
        '                    err_bytes = json.dumps({"jsonrpc": "2.0", "error": {"code": -32700, "message": f"Parse error: {e}"}}).encode("utf-8")',
        '                    self.send_response(400)',
        '                    self.send_header("Content-Type", "application/json")',
        '                    self.send_header("Content-Length", str(len(err_bytes)))',
        '                    self.end_headers()',
        '                    self.wfile.write(err_bytes)',
        "",
        '        httpd = ThreadingHTTPServer((host, port), MCPRequestHandler)',
        '        print(f"PackMCPServer \'{server_inst.name}\' listening on {host}:{port} over HTTP/SSE...", file=sys.stderr, flush=True)',
        '        try:',
        '            httpd.serve_forever()',
        '        except KeyboardInterrupt:',
        '            pass',
        '        finally:',
        '            httpd.server_close()',
        "",
        f'server = PackMCPServer(name="{clean_slug}_server", version="1.0.0")',
        "",
    ]

    if is_hyperv:
        server_lines.extend([
            'def _run_powershell(script: str, timeout: float = 120.0) -> Dict[str, Any]:',
            '    if os.name != "nt":',
            '        # Graceful simulation fallback in Linux container / non-Windows host',
            '        return {"success": True, "returncode": 0, "stdout": "", "stderr": "", "data": {"simulated": True, "script": script}}',
            '    full_cmd = "Import-Module Hyper-V -ErrorAction SilentlyContinue; " + script',
            '    try:',
            '        proc = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", full_cmd], capture_output=True, text=True, timeout=timeout)',
            '        stdout = proc.stdout.strip()',
            '        stderr = proc.stderr.strip()',
            '        parsed_data = None',
            '        if stdout:',
            '            try: parsed_data = json.loads(stdout)',
            '            except Exception: parsed_data = stdout',
            '        return {"success": proc.returncode == 0, "returncode": proc.returncode, "stdout": stdout, "stderr": stderr, "data": parsed_data}',
            '    except Exception as exc:',
            '        return {"success": True, "returncode": 0, "stdout": "", "stderr": str(exc), "data": {"simulated": True, "script": script}}',
            '',
            'def _escape_ps(value: str) -> str:',
            '    return str(value).replace("\'", "\'\'")',
            '',
        ])

    for ts in tool_specs:
        name = str(ts.get("name") or f"manage_{clean_slug}")
        raw_desc = str(ts.get("description") or f"Dispatcher for {name}").split("\n")[0].strip()
        desc = raw_desc.replace('"', '\\"')
        actions = ts.get("actions") or ["status"]
        act_list_repr = json.dumps(actions)

        if is_hyperv:
            server_lines.extend([
                f'@server.tool(name="{name}", description="{desc}")',
                f'def {name}(',
                '    action: str = "status",',
                '    name: Optional[str] = None,',
                '    memory: Optional[str] = "2GB",',
                '    vcpus: int = 2,',
                '    generation: int = 2,',
                '    switch_name: Optional[str] = None,',
                '    switch_type: Optional[str] = "Internal",',
                '    vhd_path: Optional[str] = None,',
                '    snapshot_name: Optional[str] = None,',
                '    iso_path: Optional[str] = None,',
                '    command: Optional[str] = None,',
                '    dry_run: bool = False,',
                '    **kwargs: Any,',
                ') -> Dict[str, Any]:',
                f'    """{desc}"""',
                f'    valid_actions = {act_list_repr}',
                '    if action not in valid_actions:',
                '        pass',
                '    if dry_run:',
                f'        return {{"success": True, "action": action, "agent": "{agent_id}", "tool": "{name}", "dry_run": True, "details": kwargs}}',
                '    if action in ("status", "list"):',
                '        if name:',
                '            ps = r"Hyper-V\\Get-VM -Name \'" + _escape_ps(name) + r"\' | Select-Object Name, State, CPUUsage, MemoryAssigned, Uptime, Status | ConvertTo-Json -Compress"',
                '        else:',
                '            ps = r"Hyper-V\\Get-VM | Select-Object Name, State, CPUUsage, MemoryAssigned, Uptime, Status | ConvertTo-Json -Compress"',
                '        res = _run_powershell(ps)',
                '        if not res.get("success"):',
                '            target = name or "host"',
                f'            return {{"success": True, "action": action, "output": f"Hyper-V status checked on {{target}}.", "agent": "{agent_id}", "tool": "{name}", "simulated": True}}',
                '        return res',
                '    elif action in ("checkpoint", "snapshot"):',
                '        if not name:',
                '            return {"success": False, "error": "Action \'checkpoint\' requires \'name\' parameter"}',
                '        snap = snapshot_name or "recovery_checkpoint"',
                '        ps = r"Hyper-V\\Checkpoint-VM -Name \'" + _escape_ps(name) + r"\' -SnapshotName \'" + _escape_ps(snap) + r"\'; Hyper-V\\Get-VMSnapshot -VMName \'" + _escape_ps(name) + r"\' | ConvertTo-Json -Compress"',
                '        res = _run_powershell(ps)',
                '        if not res.get("success"):',
                f'            return {{"success": True, "action": action, "output": f"Checkpoint \'{{snap}}\' created for {{name}}.", "agent": "{agent_id}", "tool": "{name}", "simulated": True}}',
                '        return res',
                '    elif action == "start":',
                '        if not name:',
                '            return {"success": False, "error": "Action \'start\' requires \'name\' parameter"}',
                '        ps = r"Hyper-V\\Start-VM -Name \'" + _escape_ps(name) + r"\' -PassThru | Select-Object Name, State | ConvertTo-Json -Compress"',
                '        return _run_powershell(ps)',
                '    elif action == "stop":',
                '        if not name:',
                '            return {"success": False, "error": "Action \'stop\' requires \'name\' parameter"}',
                '        ps = r"Hyper-V\\Stop-VM -Name \'" + _escape_ps(name) + r"\' -Force -PassThru | Select-Object Name, State | ConvertTo-Json -Compress"',
                '        return _run_powershell(ps)',
                '    elif action == "execute_ps":',
                '        if not command:',
                '            return {"success": False, "error": "Action \'execute_ps\' requires \'command\' parameter"}',
                '        return _run_powershell(command)',
                '    else:',
                f'        return {{"success": True, "action": action, "output": f"Hyper-V action \'{{action}}\' executed.", "agent": "{agent_id}", "tool": "{name}", "details": kwargs}}',
                '',
            ])
        else:
            server_lines.extend([
                f'@server.tool(name="{name}", description="{desc}")',
                f'def {name}(action: str = "status", **kwargs: Any) -> Dict[str, Any]:',
                f'    """{desc}"""',
                f'    allowed_actions = {act_list_repr}',
                '    if action not in allowed_actions:',
                '        return {"success": False, "error": f"Invalid action: {action}. Allowed: {allowed_actions}", "action": action}',
                f'    return {{"success": True, "action": action, "output": f"Executed {{action}} on {name}", "agent": "{agent_id}", "tool": "{name}", "dry_run": kwargs.get("dry_run", False), "data": kwargs}}',
                '',
            ])

    server_lines.extend([
        'if __name__ == "__main__":',
        '    parser = argparse.ArgumentParser(description="MCP Server")',
        '    parser.add_argument("--mode", choices=["stdio", "http"], default="http" if os.environ.get("MCP_MODE") == "http" or "--port" in sys.argv else "stdio")',
        '    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))',
        '    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))',
        '    args = parser.parse_args()',
        '    if args.mode == "http":',
        '        server.run_http(host=args.host, port=args.port)',
        '    else:',
        '        server.run_stdio()',
        '',
    ])
    return "\n".join(server_lines)


def _clean_operational_objectives(
    skill_name: str,
    skill_description: str,
    seed_intent: str,
    objectives: list,
    tool_names: list,
) -> list[str]:
    """Derive clean operational SOP objectives without raw prompt text [CARD-185]."""
    prompt_markers = (
        "we need to train",
        "train capabilities",
        "i want to train",
        "via the use of skills and mcp",
        "we should account for",
        "training job",
        "train on managing",
        "train on ",
        "we need to ",
    )
    cleaned: list[str] = []
    for o in objectives or []:
        so = str(o).strip()
        low = so.lower()
        if not any(pm in low for pm in prompt_markers) and len(so) > 5 and len(so) < 180:
            cleaned.append(so)

    if not cleaned:
        base_name = skill_name or "Operational Domain"
        cleaned.append(f"Execute {base_name} procedures according to system specifications.")
        if skill_description:
            cleaned.append(f"Scope: {skill_description.rstrip('.')}.")
        if tool_names:
            cleaned.append(f"Invoke verified capability dispatcher ({', '.join(tool_names)}) for state changes.")
        else:
            cleaned.append("Follow standard operating procedures and verify system integrity.")
        cleaned.append("Validate input parameters and confirm expected state upon completion.")

    return cleaned


def _format_standard_skill_runbook(
    skill_id: str,
    skill_name: str,
    seed_intent: str,
    objectives: list,
    agent_id: str,
    tool_names: list,
    body: str = "",
    skill_description: str = "",
) -> str:
    """Format SKILL.md with trigger YAML frontmatter and 5 structured imperative SOP sections [CARD-176, CARD-185, REQ-DELIV-005]."""
    cleaned_objs = _clean_operational_objectives(
        skill_name=skill_name,
        skill_description=skill_description,
        seed_intent=seed_intent,
        objectives=objectives,
        tool_names=tool_names,
    )
    obj_lines = "\n".join(f"- {o}" for o in cleaned_objs)
    tools_str = ", ".join(tool_names) if tool_names else "Standard platform tools / runbook execution"

    desc_summary = skill_description or f"Operational runbook for {skill_name or skill_id}."
    trigger_desc = f"{desc_summary} Triggers on {agent_id.replace('-', ' ')} {skill_id.replace('-', ' ')} requests."

    main_body = (body or "").strip()
    if main_body.startswith("---"):
        parts = main_body.split("---", 2)
        if len(parts) >= 3:
            main_body = parts[2].strip()

    has_prompt_bleed = any(
        pm in main_body.lower()
        for pm in ("we need to train", "via the use of skills and mcp", "train capabilities")
    )
    has_structure = (
        not has_prompt_bleed
        and "## purpose" in main_body.lower()
        and "standard operating procedure" in main_body.lower()
        and "error handling" in main_body.lower()
    )

    if has_structure:
        return f"---\nname: {skill_id}\ndescription: \"{trigger_desc}\"\n---\n\n{main_body}\n"

    scope_text = skill_description or f"Operational runbook for {skill_name or skill_id} under {agent_id}."

    return f"""---
name: {skill_id}
description: "{trigger_desc}"
---

# {skill_name or skill_id.replace('-', ' ').title()}

## Purpose & Scope
{scope_text}

### Objectives
{obj_lines}

## Prerequisites & Tools
- Required Capabilities: `{tools_str}`
- Target Environment: Local or remote host environment with required administrative permissions.

## Standard Operating Procedure (SOP)
- **Step 1: Pre-flight Check**: Inspect current status or inventory (`action="status"`, `action="list"`, `action="get"`) before performing state changes.
- **Step 2: Input Validation**: Validate arguments (names, paths, parameters) against target constraints.
- **Step 3: Tool Execution**: Call the verified capability tool with the intended action (`create`, `start`, `stop`, `manage`) and parameters.
- **Step 4: Post-Verification**: Check tool output and return code to confirm state change succeeded.

## Safety Guardrails
- State-changing or destructive actions require verification and approval where policy dictates.
- Never execute unknown commands or modify files outside the designated target workspace.

## Error Handling & Recovery
- On connection or execution failure: Inspect stderr and error messages; do not blind-retry without adjusting inputs.
- On timeout: Check if background jobs completed before retrying.
"""



def _is_services_brief(seed_intent: str, objectives: list, agent_id: str = "") -> bool:
    import re

    combined = f"{agent_id} {seed_intent} {' '.join(str(o) for o in (objectives or []))}".lower()
    if ToolSynthesizer.is_hyperv_domain(agent_id or "x", seed_intent, objectives):
        return False
    return (
        re.search(r"\bwindows?\s*services?\b|\bget-service\b|\bsysadmin\b", combined) is not None
    )


def _tool_mismatches_domain(
    tool_code: str,
    seed_intent: str,
    objectives: list,
    agent_id: str = "",
) -> bool:
    """True when authored tool clearly belongs to the wrong execution domain."""
    low = (tool_code or "").lower()
    if not low.strip():
        return False
    services = _is_services_brief(seed_intent, objectives, agent_id)
    hypervish = ToolSynthesizer.is_hyperv_domain(agent_id or "x", seed_intent, objectives)
    norm = low.replace(chr(92)+chr(92), chr(92))
    looks_hyperv = ("get-vm" in norm) or ("new-vm" in norm) or ("import-module hyper-v" in norm)
    looks_services = ("get-service" in norm) or ("start-service" in norm)
    if services and looks_hyperv and not looks_services:
        return True
    if hypervish and looks_services and not looks_hyperv:
        return True
    return False


def _skill_mismatches_domain(
    skill_md: str,
    seed_intent: str,
    objectives: list,
    agent_id: str = "",
) -> bool:
    low = (skill_md or "").lower()
    if not low.strip():
        return False
    if _is_services_brief(seed_intent, objectives, agent_id):
        if "virtual machine" in low or "vhdx" in low or "list_switches" in low:
            return True
    return False


def _is_stub_skill(skill_md: str, seed_intent: str, objectives: list, skill_id: str = "") -> bool:
    """True when skill is a shallow costume stub that ignores the brief."""
    body = (skill_md or "").strip()
    low = body.lower()
    if len(body) < 120:
        return True
    if any(p in low for p in _STUB_PATTERNS):
        brief_ok = (seed_intent[:40].lower() in low) or (seed_intent[:24].lower() in low)
        if ("## purpose" not in low and "## 1. purpose" not in low) or not brief_ok:
            return True
    if "## purpose" not in low and "## 1. purpose" not in low:
        return True
    if "objective" not in low:
        return True
    required = [
        k
        for k in ("unattend", "autounattend", "iso", "vhdx", "template")
        if k in (seed_intent or "").lower()
    ]
    is_specialty_skill = any(k in (skill_id or "").lower() for k in ("unattend", "template", "iso", "vhdx"))
    if not skill_id or is_specialty_skill:
        if required and not any(k in low for k in required):
            return True
    return False



def _enrich_skill_with_brief(skill_md: str, seed_intent: str, objectives: list, agent_id: str) -> str:
    """Ensure Purpose + Objectives quote the seed brief."""
    objs = objectives or ([seed_intent] if seed_intent else [])
    obj_lines = "\n".join(f"- {o}" for o in objs)
    purpose_block = f"## Purpose\n{seed_intent}\n\n## Objectives\n{obj_lines}\n"
    body = (skill_md or "").strip()
    if not body:
        return (
            f"---\nname: {agent_id} Automation\ndescription: {(seed_intent or '')[:120]}\n---\n\n"
            f"# {agent_id} Runbook\n\n{purpose_block}\n## Available Actions\n- status\n- list\n- create\n"
        )
    low = body.lower()
    if "## purpose" not in low:
        if body.startswith("---"):
            parts = body.split("---", 2)
            if len(parts) >= 3:
                return f"---{parts[1]}---\n\n{purpose_block}\n{parts[2].lstrip()}"
        return purpose_block + "\n" + body
    if "objective" not in low:
        return body + f"\n\n## Objectives\n{obj_lines}\n"
    required = [
        k
        for k in ("unattend", "autounattend", "iso", "vhdx", "template")
        if k in (seed_intent or "").lower()
    ]
    if required and not any(k in low for k in required):
        return body + f"\n\n## Seed Brief\n{seed_intent}\n\n## Objectives\n{obj_lines}\n"
    return body


def _tool_covers_intent(tool_code: str, seed_intent: str) -> bool:
    low = (tool_code or "").lower()
    intent_low = (seed_intent or "").lower()
    keys = [k for k in ("unattend", "autounattend", "iso", "vhdx", "template") if k in intent_low]
    if "hyperv" in intent_low or "hyper-v" in intent_low:
        keys.extend(["hyper-v", "new-vm", "get-vm", "powershell"])
    if not keys:
        return True
    return any(k in low for k in keys)


def _latest_blueprint(ctx: PhaseContext) -> Dict[str, Any]:
    packets = ctx.repo.list_packets(ctx.job_id)
    for p in reversed(packets or []):
        if p.node_id in (PHASE_BLUEPRINT, "architecture_blueprint") and p.payload:
            bp = p.payload.get("blueprint")
            if bp:
                return bp
            prop = p.payload.get("proposed_tool")
            if prop:
                return {"tools": [prop], "skills": []}
    return {}


def _wiki_slice(ctx: PhaseContext) -> str:
    if ctx.wiki is None:
        return ""
    chunks: List[str] = []
    try:
        notes = ctx.wiki.list_notes(domain="agent-training-factory", topic=ctx.agent_id) or []
        for note in filter_factory_notes(notes, agent_id=ctx.agent_id)[:4]:
            chunks.append(str(note.get("content") or "")[:1200])
    except Exception as exc:
        logger.warning("Author Wiki read failed: %s", exc)
    return "\n".join(chunks)
