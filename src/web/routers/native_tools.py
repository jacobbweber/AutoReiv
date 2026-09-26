"""Native custom tool HTTP API [CARD-423].

Same NativeCustomToolService the developer tool calls. MCP attach stays on
/api/settings/mcp and /api/agents/{id}/mcp.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.application.tools.native_packaging import NativeToolCheckFailed, NativeToolError

router = APIRouter(prefix="/api/tools/native", tags=["Native custom tools"])


class NativeToolRegisterRequest(BaseModel):
    name: str
    description: str
    code: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    requires_hitl: bool = True
    risk_level: str = "medium"
    grant_agent_ids: list[str] = Field(default_factory=list)
    # CARD-511 tool check: sample input, or skip the sample call with a reason.
    sample_arguments: Optional[dict[str, Any]] = None
    sample_call: str = "run"
    skip_reason: str = ""


class NativeToolInvokeRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)
    agent_id: str
    approval_mode: str = "ask"
    session_id: Optional[str] = None


class NativeFolderPlanRequest(BaseModel):
    directory: str


def _service(request: Request):
    service = getattr(request.app.state, "native_custom_tools", None)
    if service is None:
        raise HTTPException(status_code=503, detail={"message": "Native tool packaging is unavailable."})
    return service


def _http(exc: NativeToolError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail={"message": str(exc)})


@router.get("")
def list_native_tools(request: Request) -> dict[str, Any]:
    try:
        tools = _service(request).list_tools()
    except NativeToolError as exc:
        raise _http(exc) from exc
    return {"tools": tools, "packaging": "native", "mcp_required": False}


@router.post("")
async def register_native_tool(payload: NativeToolRegisterRequest, request: Request) -> dict[str, Any]:
    try:
        return await _service(request).register(payload.model_dump())
    except NativeToolCheckFailed as exc:
        # CARD-511: the tool failed its one sandbox run and was not registered.
        raise HTTPException(status_code=422, detail={"message": str(exc), "check": exc.check}) from exc
    except NativeToolError as exc:
        raise _http(exc) from exc


@router.post("/plan")
def plan_native_folder(payload: NativeFolderPlanRequest, request: Request) -> dict[str, Any]:
    try:
        return _service(request).plan_folder(payload.directory)
    except NativeToolError as exc:
        raise _http(exc) from exc


@router.delete("/{name}")
def delete_native_tool(name: str, request: Request) -> dict[str, Any]:
    try:
        return _service(request).delete(name)
    except NativeToolError as exc:
        raise _http(exc) from exc


@router.post("/{name}/invoke")
async def invoke_native_tool(name: str, payload: NativeToolInvokeRequest, request: Request) -> dict[str, Any]:
    try:
        return await _service(request).invoke(
            name,
            payload.arguments,
            payload.agent_id,
            approval_mode=payload.approval_mode,
            session_id=payload.session_id,
        )
    except NativeToolError as exc:
        raise _http(exc) from exc
