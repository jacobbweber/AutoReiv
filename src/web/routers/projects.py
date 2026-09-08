"""
Projects studio API [REQ-SDLC-050, REQ-SDLC-051, REQ-SDLC-052].
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.application.sdlc.paths import ProjectPathError, jail_join
from src.application.sdlc.projects_service import ProjectsService

NOISE_DIRS = {".git", "__pycache__", "node_modules", ".venv", ".pytest_cache", ".ruff_cache"}
READ_MAX_CHARS = 100000

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


@router.get("/api/projects/files/list")
async def get_project_files_list(request: Request, path: str = ".", category: Optional[str] = None):
    """List directory entries clamped inside the active project root [REQ-PROJ-014]."""
    svc = _service(request)
    root = svc.resolve_root()
    if root is None or not root.exists():
        raise HTTPException(status_code=400, detail="No active project selected or project directory not found")

    target = root
    target_rel = "."

    if category and category.strip().lower() not in ("", "all"):
        cat = category.strip().lower()
        if cat == "cards":
            target = root / ".agents" / "cards"
            if not target.exists():
                target = root / ".github" / "cards"
        elif cat == "specs":
            target = root / ".agents" / "specs"
            if not target.exists():
                target = root / "docs" / "specs"
        elif cat == "steering":
            target = root / ".agents" / "steering"
        elif cat in ("adr", "adrs"):
            target = root / ".agents" / "adr"
            if not target.exists():
                target = root / "docs" / "adr"
        else:
            raise HTTPException(status_code=400, detail=f"Unknown category: {category}")

        if not target.exists():
            return {
                "success": True,
                "project_root": str(root),
                "path": str(target.relative_to(root)).replace("\\", "/") if target.is_relative_to(root) else ".",
                "category": cat,
                "entries": [],
            }
        target_rel = str(target.relative_to(root)).replace("\\", "/")
    else:
        try:
            target = jail_join(root, path or ".")
        except ProjectPathError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if not target.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {path}")
        target_rel = str(target.relative_to(root)).replace("\\", "/") if target != root else "."

    if not target.is_dir():
        return {
            "success": True,
            "project_root": str(root),
            "path": target_rel,
            "category": category or "all",
            "entries": [
                {
                    "name": target.name,
                    "path": target_rel,
                    "type": "file",
                    "ext": target.suffix.lower(),
                }
            ],
        }

    entries = []
    for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if child.name in NOISE_DIRS:
            continue
        rel = str(child.relative_to(root)).replace("\\", "/")
        entries.append(
            {
                "name": child.name,
                "path": rel,
                "type": "dir" if child.is_dir() else "file",
                "ext": child.suffix.lower() if child.is_file() else "",
            }
        )

    return {
        "success": True,
        "project_root": str(root),
        "path": target_rel,
        "category": category or "all",
        "entries": entries,
    }


@router.get("/api/projects/files/read")
async def get_project_file_content(request: Request, path: str):
    """Read UTF-8 file content clamped inside the active project root [REQ-PROJ-014]."""
    if not path or not path.strip():
        raise HTTPException(status_code=400, detail="path parameter is required")

    svc = _service(request)
    root = svc.resolve_root()
    if root is None or not root.exists():
        raise HTTPException(status_code=400, detail="No active project selected or project directory not found")

    try:
        target = jail_join(root, path.strip())
    except ProjectPathError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {exc}")

    is_markdown = target.suffix.lower() == ".md"
    truncated = len(text) > READ_MAX_CHARS

    return {
        "success": True,
        "project_root": str(root),
        "path": str(target.relative_to(root)).replace("\\", "/"),
        "name": target.name,
        "ext": target.suffix.lower(),
        "content": text[:READ_MAX_CHARS],
        "chars": len(text),
        "truncated": truncated,
        "is_markdown": is_markdown,
    }

