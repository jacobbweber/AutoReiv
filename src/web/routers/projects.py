"""
Projects studio API [REQ-SDLC-050, REQ-SDLC-051, REQ-SDLC-052].
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.application.sdlc.projects_service import ProjectsService

router = APIRouter(tags=["Projects"])


class ProjectsRootRequest(BaseModel):
    path: str = ""


class CreateProjectRequest(BaseModel):
    slug: str
    name: Optional[str] = None


class SelectProjectRequest(BaseModel):
    slug: Optional[str] = None
    path: Optional[str] = None


def _service(request: Request) -> ProjectsService:
    svc = getattr(request.app.state, "projects_service", None)
    if svc is None:
        svc = ProjectsService(store=request.app.state.store)
        request.app.state.projects_service = svc
    return svc


@router.get("/api/settings/projects_root")
async def get_projects_root(request: Request):
    svc = _service(request)
    return {"projects_root": svc.get_projects_root(), "placeholder": r"D:\Projects\Active"}


@router.put("/api/settings/projects_root")
async def put_projects_root(request: Request, req: ProjectsRootRequest):
    svc = _service(request)
    return svc.set_projects_root(req.path)


@router.get("/api/projects")
async def list_projects(request: Request):
    return _service(request).list_projects()


@router.post("/api/projects")
async def create_project(request: Request, req: CreateProjectRequest):
    res = _service(request).create_project(slug=req.slug, name=req.name)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "create failed"))
    return res


@router.delete("/api/projects/{slug}")
async def delete_project(request: Request, slug: str, confirm: bool = False):
    res = _service(request).delete_project(slug=slug, confirm=confirm)
    if not res.get("success"):
        code = 400 if "confirm" in (res.get("error") or "") else 404
        if "confirm" in (res.get("error") or ""):
            code = 400
        elif "not found" in (res.get("error") or "").lower():
            code = 404
        else:
            code = 400
        raise HTTPException(status_code=code, detail=res.get("error", "delete failed"))
    return res


@router.get("/api/projects/selected")
async def get_selected_project(request: Request):
    return {"selected": _service(request).get_selected()}


@router.put("/api/projects/selected")
async def put_selected_project(request: Request, req: SelectProjectRequest):
    res = _service(request).set_selected(slug=req.slug, path=req.path)
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error", "not found"))
    return res
