"""
AutoReiv Hosted MCP Server Router [CARD-392, REQ-392-001..005].
Implements official Model Context Protocol (MCP) HTTP/SSE server transport,
publishing agent-mediated dispatchers (ask_<agent_id>) and safe passive lookups.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp", tags=["hosted-mcp-server"])

# Active SSE client queues: session_id -> asyncio.Queue
_active_sessions: Dict[str, asyncio.Queue] = {}
_active_sessions_lock = asyncio.Lock()

# Retired legacy agents not published to MCP
RETIRED_AGENT_IDS = Object_freeze = frozenset([
    "agent-builder",
    "coding",
    "review",
    "conductor",
    "hyperv",
    "assistant",
    "wiki",
    "direct",  # Direct mode has no tools/autonomous loop
])


def _check_auth(request: Request, token_param: Optional[str] = None) -> bool:
    """Verify inbound bearer token or API key if configured in settings."""
    store = getattr(request.app.state, "store", None)
    if not store:
        return True
    settings = store.get_setting("hosted_mcp") or {}
    required_token = (settings.get("api_token") or "").strip()
    if not required_token:
        return True

    # Check Authorization: Bearer <token>
    auth_header = request.headers.get("authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        provided = auth_header[7:].strip()
        if provided == required_token:
            return True

    # Check x-api-key header
    if request.headers.get("x-api-key", "").strip() == required_token:
        return True

    # Check query param
    if (token_param or "").strip() == required_token:
        return True

    return False


def _get_published_agents(request: Request) -> List[Any]:
    """Retrieve chat-visible agents with autonomous capabilities."""
    registry = getattr(request.app.state, "registry", None)
    store = getattr(request.app.state, "store", None)
    agents: List[Any] = []

    if registry and hasattr(registry, "list_agents"):
        try:
            agents = list(registry.list_agents())
        except Exception:
            pass

    if not agents and store and hasattr(store, "list_agents"):
        try:
            agents = list(store.list_agents())
        except Exception:
            pass

    published: List[Any] = []
    seen_ids = set()
    for agent in agents:
        agent_id = getattr(agent, "id", None)
        if not agent_id or agent_id in seen_ids:
            continue
        if agent_id in RETIRED_AGENT_IDS:
            continue
        if getattr(agent, "visibility", "public") == "internal":
            continue
        seen_ids.add(agent_id)
        published.append(agent)

    return published


def _build_tools_list(request: Request) -> List[Dict[str, Any]]:
    """Assemble MCP tools list: agent dispatchers + safe passive lookups."""
    tools: List[Dict[str, Any]] = []

    # 1. Agent Dispatch Tools (ask_<agent_id>)
    agents = _get_published_agents(request)
    for agent in agents:
        agent_id = str(agent.id).replace("-", "_")
        name = f"ask_{agent_id}"
        agent_name = getattr(agent, "name", agent.id)
        description = (
            getattr(agent, "description", "")
            or f"{agent_name} specialist agent."
        ).strip()
        tools.append({
            "name": name,
            "description": f"{agent_name}: {description} Runs autonomous turns with local skills, project tools, and AGENTS.md governance.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": f"The task, question, or instructions for {agent_name}.",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional conversation session ID for multi-turn continuity.",
                    },
                },
                "required": ["prompt"],
            },
        })

    # 2. Safe Passive Wiki Search Tool
    tools.append({
        "name": "search_wiki",
        "description": "Search AutoReiv's local markdown knowledge base vault by query keywords.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query keywords or topic name.",
                },
            },
            "required": ["query"],
        },
    })

    # 3. Safe Passive Wiki Read Tool
    tools.append({
        "name": "read_wiki_document",
        "description": "Read the full markdown text of a document in AutoReiv's local knowledge base vault.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative file path of the document (e.g. '01-Projects/alpha.md').",
                },
            },
            "required": ["path"],
        },
    })

    # 4. Safe System Diagnostics Tool
    tools.append({
        "name": "get_system_health",
        "description": "Retrieve system health status, active agents count, and hardware metrics from this AutoReiv instance.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    })

    return tools


async def _execute_tool_call(request: Request, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute tool call: route agent dispatchers to AgentKernel.run_turn, or passive tools."""
    # Agent Dispatcher
    if name.startswith("ask_"):
        agent_slug = name[4:].replace("_", "-")
        registry = getattr(request.app.state, "registry", None)
        agent = None
        if registry and hasattr(registry, "get_agent"):
            agent = registry.get_agent(agent_slug)
            if not agent:
                agent = registry.get_agent(name[4:])

        if not agent:
            store = getattr(request.app.state, "store", None)
            if store and hasattr(store, "get_agent"):
                agent = store.get_agent(agent_slug)

        if not agent:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Agent '{agent_slug}' is not recognized or installed on this AutoReiv instance."}],
            }

        prompt = arguments.get("prompt") or arguments.get("message") or ""
        if not prompt.strip():
            return {
                "isError": True,
                "content": [{"type": "text", "text": "Missing required argument 'prompt'."}],
            }

        kernel = getattr(request.app.state, "kernel", None)
        if not kernel or not hasattr(kernel, "run_turn"):
            return {
                "isError": True,
                "content": [{"type": "text", "text": "AgentKernel execution engine is unavailable on this instance."}],
            }

        session_id = arguments.get("session_id") or f"mcp-remote-{uuid.uuid4().hex[:8]}"
        try:
            chat_msg = await kernel.run_turn(
                agent=agent,
                session_id=session_id,
                user_content=prompt,
                save_to_history=True,
                approval_mode="auto",
            )
            output_text = (chat_msg.content or "").strip()
            return {
                "isError": False,
                "content": [{"type": "text", "text": output_text or "(Agent completed turn with empty message)"}],
            }
        except Exception as exc:
            logger.error(f"Hosted MCP execution of '{name}' failed: {exc}", exc_info=True)
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Execution error in {agent_slug}: {str(exc)}"}],
            }

    # Passive Wiki Search
    if name == "search_wiki":
        query = str(arguments.get("query") or "").strip()
        if not query:
            return {"isError": True, "content": [{"type": "text", "text": "Query parameter is required."}]}
        wiki_svc = getattr(request.app.state, "wiki_service", None)
        if wiki_svc and hasattr(wiki_svc, "search"):
            results = wiki_svc.search(query, limit=5)
            formatted = json.dumps(results, indent=2)
            return {"isError": False, "content": [{"type": "text", "text": formatted}]}
        return {"isError": True, "content": [{"type": "text", "text": "WikiService is unavailable."}]}

    # Passive Wiki Read
    if name == "read_wiki_document":
        path = str(arguments.get("path") or "").strip()
        if not path:
            return {"isError": True, "content": [{"type": "text", "text": "Path parameter is required."}]}
        wiki_svc = getattr(request.app.state, "wiki_service", None)
        if wiki_svc and hasattr(wiki_svc, "get_note"):
            note = wiki_svc.get_note(path)
            content = (note or {}).get("content", "")
            return {"isError": False, "content": [{"type": "text", "text": content or f"Document '{path}' is empty or not found."}]}
        return {"isError": True, "content": [{"type": "text", "text": "WikiService is unavailable."}]}

    # System Health
    if name == "get_system_health":
        store = getattr(request.app.state, "store", None)
        registry = getattr(request.app.state, "registry", None)
        active_agents = len(_get_published_agents(request))
        health_data = {
            "status": "healthy",
            "server": "AutoReiv Hosted MCP Server",
            "active_agents_count": active_agents,
            "mcp_transport": "HTTP/SSE",
            "active_sse_connections": len(_active_sessions),
        }
        return {"isError": False, "content": [{"type": "text", "text": json.dumps(health_data, indent=2)}]}

    return {
        "isError": True,
        "content": [{"type": "text", "text": f"Tool '{name}' is not recognized by this MCP server."}],
    }


async def _handle_single_jsonrpc(request: Request, msg: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    """Process a single JSON-RPC 2.0 message."""
    req_id = msg.get("id")
    method = msg.get("method", "")
    params = msg.get("params") or {}

    # 1. initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {},
                    "prompts": {},
                },
                "serverInfo": {
                    "name": "AutoReiv Hosted MCP Server",
                    "version": "1.0.0",
                },
            },
        }

    # 2. notifications/initialized
    if method == "notifications/initialized":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    # 3. ping
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    # 4. tools/list
    if method == "tools/list":
        tools_list = _build_tools_list(request)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": tools_list},
        }

    # 5. tools/call
    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments") or {}
        call_result = await _execute_tool_call(request, tool_name, arguments)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": call_result,
        }

    # 6. resources/list
    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": []}}

    # 7. prompts/list
    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": []}}

    # Method not found
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": -32601,
            "message": f"Method '{method}' not found.",
        },
    }


@router.get("/sse")
async def mcp_sse_handshake(
    request: Request,
    session_id: Optional[str] = None,
    token: Optional[str] = Query(None),
    handshake_only: bool = Query(False),
):
    """
    Model Context Protocol (MCP) Server-Sent Events (SSE) stream [REQ-392-001].
    Establishes SSE session, yields endpoint URL event, and streams message payloads.
    """
    if not _check_auth(request, token_param=token):
        return Response(content="Unauthorized", status_code=401)

    sid = session_id or uuid.uuid4().hex[:16]
    client_queue: asyncio.Queue = asyncio.Queue()

    async with _active_sessions_lock:
        _active_sessions[sid] = client_queue

    async def event_generator():
        try:
            # 1. Send initial endpoint event pointing to messages POST handler
            yield f"event: endpoint\r\ndata: /api/mcp/messages?session_id={sid}\r\n\r\n"
            if handshake_only:
                return

            # 2. Main event loop: stream queued messages or send keepalive
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(client_queue.get(), timeout=1.0)
                    yield f"event: message\r\ndata: {json.dumps(msg)}\r\n\r\n"
                    client_queue.task_done()
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        break
                    yield ": keepalive\r\n\r\n"
        except asyncio.CancelledError:
            logger.info(f"Hosted MCP SSE client disconnected: session={sid}")
            raise
        finally:
            async with _active_sessions_lock:
                _active_sessions.pop(sid, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/messages")
@router.post("/sse")
async def mcp_messages_handler(
    request: Request,
    session_id: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
):
    """
    Process incoming JSON-RPC 2.0 messages from external MCP clients [REQ-392-002, REQ-392-003].
    Dual-mode: returns response directly via HTTP 200 AND dispatches to active SSE session stream.
    """
    if not _check_auth(request, token_param=token):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error: Invalid JSON payload"},
            },
        )

    # Handle batch vs single message
    if isinstance(body, list):
        results = [await _handle_single_jsonrpc(request, item, session_id=session_id) for item in body]
        # Dispatch to active SSE queue if connected
        if session_id and session_id in _active_sessions:
            for res in results:
                await _active_sessions[session_id].put(res)
        return JSONResponse(content=results)

    result = await _handle_single_jsonrpc(request, body, session_id=session_id)
    # Dispatch to active SSE queue if connected
    if session_id and session_id in _active_sessions:
        await _active_sessions[session_id].put(result)

    return JSONResponse(content=result)


@router.get("/status")
async def mcp_status_handler(request: Request):
    """Retrieve Hosted MCP Server status and published capabilities [REQ-392-004]."""
    store = getattr(request.app.state, "store", None)
    settings = (store.get_setting("hosted_mcp") or {}) if store else {}
    published = _get_published_agents(request)

    return {
        "status": "active",
        "hosted_server": {
            "endpoint": "/api/mcp/sse",
            "messages_endpoint": "/api/mcp/messages",
            "protocol_version": "2024-11-05",
            "auth_required": bool(settings.get("api_token")),
            "published_agents": [getattr(a, "id", "") for a in published],
            "published_tools_count": len(_build_tools_list(request)),
            "active_sse_clients": len(_active_sessions),
        },
    }
