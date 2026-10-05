"""
Projects studio API [REQ-SDLC-050, REQ-SDLC-051, REQ-SDLC-052].
"""

from pathlib import Path
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




@router.get("/api/projects/browse")
async def browse_project_folders(request: Request, path: str = "."):
    """Folder-only tree under projects_root with up/back [CARD-300]."""
    return _service(request).browse_folders(relative=path)



@router.get("/api/projects/drift")
async def get_project_drift(request: Request):
    """Structure-only template drift for the active project [CARD-302]."""
    return _service(request).detect_drift()


@router.post("/api/projects/align")
async def align_active_project(request: Request):
    """Scaffold missing manifest paths into the active project (adopt/align)."""
    res = _service(request).align_project()
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "align failed"))
    return res

@router.get("/api/projects/files/list")
async def get_project_files_list(request: Request, path: str = ".", category: Optional[str] = None):
    """List directory entries clamped inside the active project root [REQ-PROJ-014]."""
    svc = _service(request)
    try:
        root = svc.require_selected_root()
    except ProjectPathError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    target = root
    target_rel = "."

    if category and category.strip().lower() not in ("", "all"):
        cat = category.strip().lower()
        if cat == "cards":
            target = root / ".agents" / "cards"
            for legacy in (root / "docs" / "cards", root / ".github" / "cards"):
                if not target.exists():
                    target = legacy
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
    try:
        root = svc.require_selected_root()
    except ProjectPathError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

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


# --- CARD-634: journey runs (CARD-532 reports via CARD-632 reader) -----------------


@router.get("/api/projects/journey-runs")
async def list_journey_runs(request: Request, limit: int = 30):
    """List CARD-532 live QA journey report folders (local mtime, pass/fail, failing step)."""
    from src.application.skills.journey_qa_tools import JourneyQaTools

    tools = JourneyQaTools()
    listed = tools.list_journey_reports(limit=limit)
    rows = []
    for r in listed.get("reports") or []:
        failing = ""
        if r.get("overall") == "fail":
            summ = tools.summarize_journey_failures(r.get("card") or "")
            fails = summ.get("failures") or []
            if fails:
                failing = str(fails[0].get("step") or "")
        rows.append(
            {
                "card": r.get("card"),
                "mtime": r.get("mtime"),
                "started_at": r.get("started_at"),
                "overall": r.get("overall"),
                "failed_runs": r.get("failed_runs"),
                "run_count": r.get("run_count"),
                "failing_step": failing,
                "path": r.get("path"),
            }
        )
    return {"success": True, "report_root": listed.get("report_root"), "runs": rows}


@router.get("/api/projects/journey-runs/{card}")
async def get_journey_run(card: str, request: Request):
    """One journey report plus screenshot file names under its folder."""
    from src.application.skills.journey_qa_tools import JourneyQaTools

    tools = JourneyQaTools()
    read = tools.read_journey_report(card)
    if not read.get("success"):
        raise HTTPException(status_code=404, detail=read.get("error", "not found"))
    folder = Path(read["path"]).parent
    shots = []
    try:
        for p in sorted(folder.iterdir()):
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"} and p.is_file():
                shots.append({"name": p.name, "path": str(p), "mtime": p.stat().st_mtime})
    except OSError:
        shots = []
    summ = tools.summarize_journey_failures(card)
    return {
        "success": True,
        "card": folder.name,
        "report": read,
        "summary": summ.get("summary") if summ.get("success") else "",
        "failures": summ.get("failures") if summ.get("success") else [],
        "screenshots": shots,
        "report_root": tools.report_root.as_posix() if hasattr(tools.report_root, "as_posix") else str(tools.report_root),
    }
