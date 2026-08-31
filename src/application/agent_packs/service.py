"""Import, export, and scaffold one Agent Pack folder or zip."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from src.application.agent_packs.schema import (
    FORBIDDEN_PACK_KEYS,
    PACK_SCHEMA_VERSION,
    SKIP_PACK_SUFFIXES,
    AgentPackManifest,
    PackSkill,
)
from src.domain.agents.guardrails import AgentProfileGuardrail, AgentValidationError
from src.domain.kernel.models import AgentProfile
from src.domain.settings.models import AgentCustomization

_SAFE_ID = re.compile(r"^[a-zA-Z0-9._-]+$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_id(value: str) -> str:
    text = (value or "").strip()
    if not text or not _SAFE_ID.match(text):
        raise ValueError(f"Invalid id {value!r}. Use letters, digits, dot, underscore, hyphen.")
    return text


def _strip_forbidden(payload: Any) -> Any:
    """Drop instance facts / secrets from nested dicts before writing a pack."""
    if isinstance(payload, dict):
        return {k: _strip_forbidden(v) for k, v in payload.items() if k not in FORBIDDEN_PACK_KEYS}
    if isinstance(payload, list):
        return [_strip_forbidden(item) for item in payload]
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _is_python_or_binary_tool(path: Path) -> bool:
    return path.suffix.lower() in SKIP_PACK_SUFFIXES


def _split_inline_skills(raw: Any) -> Tuple[Optional[List[Dict[str, Any]]], Optional[List[Dict[str, Any]]]]:
    """Split authoring skills into SKILL.md bodies and nested pack.json skill objects."""
    if not isinstance(raw, list):
        return None, None
    bodies: List[Dict[str, Any]] = []
    pack_skills: List[Dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            sid = item.strip()
            if not sid:
                continue
            bodies.append({"id": sid, "name": sid})
            pack_skills.append({"id": sid, "tools": []})
            continue
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id") or item.get("name") or "").strip()
        if not sid:
            continue
        bodies.append(item)
        pack_skills.append(
            {
                "id": sid,
                "name": str(item.get("name") or sid).strip(),
                "description": str(item.get("description") or item.get("blurb") or "").strip(),
                "tools": item.get("tools") or [],
            }
        )
    return bodies, pack_skills


class AgentPackService:
    """Write and read one specialist pack. Does not add a kernel primitive."""

    def __init__(
        self,
        data_dir: Union[str, Path],
        agent_registry: Any = None,
        store: Any = None,
        available_tools: Optional[set[str]] = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.agent_registry = agent_registry
        self.store = store if store is not None else getattr(agent_registry, "state_store", None)
        self.available_tools = available_tools
        self.skills_dir = self.data_dir / "skills"
        self.agents_dir = self.data_dir / "agents"
        self.packs_dir = self.data_dir / "packs"

    def pack_dir(self, pack_id: str) -> Path:
        return self.packs_dir / _safe_id(pack_id)

    def manifest_from_profile(
        self,
        profile: AgentProfile,
        skill_tools: Optional[Dict[str, List[str]]] = None,
    ) -> AgentPackManifest:
        tone = profile.tone.value if hasattr(profile.tone, "value") else str(profile.tone)
        purpose = profile.purpose.value if hasattr(profile.purpose, "value") else str(profile.purpose)
        skill_ids = list(profile.allowed_skill or [])
        pack_tools = list(profile.pack_tool_names or [])
        mapping = skill_tools if isinstance(skill_tools, dict) else {}
        skills = [PackSkill(id=sid, tools=list(mapping.get(sid) or [])) for sid in skill_ids]
        return AgentPackManifest(
            schema_version=PACK_SCHEMA_VERSION,
            id=profile.id,
            name=profile.name,
            description=profile.description or "",
            system_prompt=profile.system_prompt or "",
            tone=tone,
            purpose=purpose,
            avatar_icon=profile.avatar_icon or "bot",
            model=profile.model or "default",
            skills=skills,
            allowed_skill=skill_ids,
            pack_tool_names=pack_tools,
            show_in_chat=profile.show_in_chat is not False,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    def _stored_skill_tools(self, pack_id: str) -> Dict[str, List[str]]:
        path = self.pack_dir(pack_id) / "pack.json"
        if not path.is_file():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        mapping: Dict[str, List[str]] = {}
        for item in raw.get("skills") or []:
            if not isinstance(item, dict):
                continue
            sid = str(item.get("id") or "").strip()
            if not sid:
                continue
            tools = item.get("tools") or []
            if isinstance(tools, str):
                tools = [tools]
            mapping[sid] = [str(t).strip() for t in tools if str(t).strip()]
        return mapping

    def _persist_pack_manifest(self, manifest: AgentPackManifest) -> None:
        dest = self.pack_dir(manifest.id)
        dest.mkdir(parents=True, exist_ok=True)
        payload = manifest.model_dump(mode="json")
        payload["schema_version"] = PACK_SCHEMA_VERSION
        _write_json(dest / "pack.json", payload)

    def _resolve_profile(self, agent_id: str) -> AgentProfile:
        if self.agent_registry is None:
            raise ValueError("Agent registry is required to export a pack.")
        profile = self.agent_registry.get_agent(agent_id)
        if profile is None:
            raise KeyError(f"Agent '{agent_id}' not found.")
        return profile

    def export_folder(self, agent_id: str, dest_dir: Optional[Union[str, Path]] = None) -> Path:
        """Write a pack folder for the agent. Returns the folder path."""
        profile = self._resolve_profile(agent_id)
        stored_map = self._stored_skill_tools(profile.id)
        dest = Path(dest_dir) if dest_dir is not None else self.pack_dir(profile.id)
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)

        manifest = self.manifest_from_profile(profile, skill_tools=stored_map)
        _write_json(dest / "pack.json", manifest.model_dump(mode="json"))
        self._copy_skills_out(manifest.allowed_skill, dest / "skills")
        self._copy_workflows_out(profile.id, dest / "workflows")
        return dest

    def export_zip(self, agent_id: str, dest_zip: Optional[Union[str, Path]] = None) -> Path:
        """Write a zip of the pack folder. Returns the zip path."""
        profile = self._resolve_profile(agent_id)
        zip_path = Path(dest_zip) if dest_zip is not None else self.packs_dir / f"{_safe_id(profile.id)}.zip"
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        folder = self.export_folder(agent_id)
        _zip_dir(folder, zip_path)
        return zip_path

    def import_path(self, source: Union[str, Path]) -> AgentProfile:
        """Import a pack zip or folder. Create/update the specialist in user data."""
        src = Path(source)
        if not src.exists():
            raise FileNotFoundError(f"Pack source not found: {src}")
        tmp_extract: Optional[Path] = None
        try:
            if src.is_file():
                tmp_extract = Path(tempfile.mkdtemp(prefix="autoreiv-pack-"))
                folder = _extract_pack_zip(src, tmp_extract)
            else:
                folder = src
            return self._import_folder(folder)
        finally:
            if tmp_extract is not None:
                shutil.rmtree(tmp_extract, ignore_errors=True)

    def scaffold_pack(self, spec: Dict[str, Any], dest_dir: Optional[Union[str, Path]] = None) -> Path:
        """Write a pack folder from a structured spec (identity, nested skills, tools, Show in Chat)."""
        data = dict(spec or {})
        inline_workflows = data.pop("workflows", None)
        inline_skills, pack_skills = _split_inline_skills(data.get("skills"))
        if pack_skills is not None:
            data["skills"] = pack_skills
        manifest = AgentPackManifest.model_validate(data)
        dest = Path(dest_dir) if dest_dir is not None else self.pack_dir(manifest.id)
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)

        skills_root = dest / "skills"
        skill_ids = list(manifest.allowed_skill)
        if isinstance(inline_skills, list):
            for item in inline_skills:
                if isinstance(item, str):
                    if item.strip() and item.strip() not in skill_ids:
                        skill_ids.append(item.strip())
                    continue
                if not isinstance(item, dict):
                    continue
                skill_id = str(item.get("id") or item.get("name") or "").strip()
                if not skill_id:
                    continue
                if skill_id not in skill_ids:
                    skill_ids.append(skill_id)
                self._write_skill_md(skills_root / skill_id / "SKILL.md", item)

        for skill_id in skill_ids:
            target = skills_root / skill_id / "SKILL.md"
            if target.is_file():
                continue
            existing = self.skills_dir / skill_id / "SKILL.md"
            if existing.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(existing, target)
            else:
                self._write_skill_md(
                    target,
                    {
                        "id": skill_id,
                        "name": skill_id,
                        "description": f"Runbook for {skill_id}.",
                        "body": (f"# {skill_id}\n\nOrder the work, name pitfalls, and state done-when.\n"),
                    },
                )

        existing_ids = {skill.id for skill in manifest.skills}
        extra_skills = [PackSkill(id=sid, tools=[]) for sid in skill_ids if sid not in existing_ids]
        if extra_skills:
            manifest.skills = list(manifest.skills) + extra_skills
        manifest.allowed_skill = skill_ids
        manifest.schema_version = PACK_SCHEMA_VERSION
        _write_json(dest / "pack.json", manifest.model_dump(mode="json"))

        if isinstance(inline_workflows, list):
            wf_root = dest / "workflows"
            wf_root.mkdir(parents=True, exist_ok=True)
            for workflow in inline_workflows:
                if not isinstance(workflow, dict):
                    continue
                wf_id = str(workflow.get("id") or "").strip() or "wf_scaffold"
                cleaned = _strip_forbidden(dict(workflow))
                cleaned["id"] = wf_id
                cleaned["owner_agent_id"] = manifest.id
                _write_json(wf_root / f"{_safe_id(wf_id)}.json", cleaned)

        return dest

    def scaffold_and_import(self, spec: Dict[str, Any]) -> AgentProfile:
        folder = self.scaffold_pack(spec)
        return self._import_folder(folder)

    def _import_folder(self, folder: Path) -> AgentProfile:
        pack_json = folder / "pack.json"
        if not pack_json.is_file():
            raise ValueError("Pack folder is missing pack.json.")
        raw = json.loads(pack_json.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("pack.json must be an object.")
        raw = _strip_forbidden(raw)
        manifest = AgentPackManifest.model_validate(raw)
        manifest.schema_version = PACK_SCHEMA_VERSION

        self._copy_skills_in(folder / "skills")
        self._copy_workflows_in(manifest.id, folder / "workflows")
        profile = self._upsert_agent(manifest)
        self._persist_pack_manifest(manifest)
        return profile

    def _copy_skills_out(self, skill_ids: List[str], dest_root: Path) -> None:
        dest_root.mkdir(parents=True, exist_ok=True)
        for skill_id in skill_ids:
            try:
                sid = _safe_id(skill_id)
            except ValueError:
                continue
            src = self.skills_dir / sid / "SKILL.md"
            if not src.is_file():
                continue
            target = dest_root / sid / "SKILL.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)

    def _copy_skills_in(self, src_root: Path) -> None:
        if not src_root.is_dir():
            return
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        for skill_dir in sorted(src_root.iterdir()):
            if not skill_dir.is_dir():
                continue
            src = skill_dir / "SKILL.md"
            if not src.is_file():
                continue
            dest = self.skills_dir / _safe_id(skill_dir.name) / "SKILL.md"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    def _copy_workflows_out(self, agent_id: str, dest_root: Path) -> None:
        src_root = self.agents_dir / _safe_id(agent_id) / "workflows"
        dest_root.mkdir(parents=True, exist_ok=True)
        if not src_root.is_dir():
            return
        for path in sorted(src_root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            cleaned = _strip_forbidden(payload)
            _write_json(dest_root / path.name, cleaned)

    def _copy_workflows_in(self, agent_id: str, src_root: Path) -> None:
        if not src_root.is_dir():
            return
        dest_root = self.agents_dir / _safe_id(agent_id) / "workflows"
        dest_root.mkdir(parents=True, exist_ok=True)
        for path in sorted(src_root.glob("*.json")):
            if _is_python_or_binary_tool(path):
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            cleaned = _strip_forbidden(payload)
            if isinstance(cleaned, dict):
                cleaned["owner_agent_id"] = agent_id
            _write_json(dest_root / path.name, cleaned)

    def _write_skill_md(self, path: Path, spec: Dict[str, Any]) -> None:
        name = str(spec.get("name") or spec.get("id") or "skill").strip()
        description = str(spec.get("description") or spec.get("blurb") or "").strip()
        body = str(spec.get("body") or spec.get("instructions") or "").strip()
        if not body:
            body = f"# {name}\n\nOrder, pitfalls, done-when.\n"
        text = f"---\nname: {name}\ndescription: {description}\n---\n\n{body.rstrip()}\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _upsert_agent(self, manifest: AgentPackManifest) -> AgentProfile:
        if self.agent_registry is None:
            raise ValueError("Agent registry is required to import a pack.")
        existing = self.agent_registry.get_agent(manifest.id)
        pack_tools = list(manifest.pack_tool_names or [])
        if existing is not None:
            allowed_tools = list(existing.allowed_tool_names or [])
            for name in pack_tools:
                if name not in allowed_tools and (self.available_tools is None or name in self.available_tools):
                    allowed_tools.append(name)
            data = {
                "id": manifest.id,
                "name": manifest.name,
                "description": manifest.description,
                "system_prompt": manifest.system_prompt or existing.system_prompt,
                "purpose": manifest.purpose,
                "tone": manifest.tone,
                "avatar_icon": manifest.avatar_icon,
                "model": manifest.model,
                "allowed_tool_names": allowed_tools,
                "allowed_skill": list(manifest.allowed_skill or existing.allowed_skill or []),
                "pack_tool_names": pack_tools,
                "show_in_chat": manifest.show_in_chat,
                "max_turns": existing.max_turns,
                "history_retention_days": existing.history_retention_days,
                "is_builtin": existing.is_builtin,
            }
        else:
            known_pack_tools = [
                name for name in pack_tools if self.available_tools is None or name in self.available_tools
            ]
            data = {
                "id": manifest.id,
                "name": manifest.name,
                "description": manifest.description,
                "system_prompt": manifest.system_prompt
                or f"You are AutoReiv's {manifest.name}. Follow the pack runbooks.",
                "purpose": manifest.purpose,
                "tone": manifest.tone,
                "avatar_icon": manifest.avatar_icon,
                "model": manifest.model,
                "allowed_tool_names": known_pack_tools,
                "allowed_skill": list(manifest.allowed_skill or []),
                "pack_tool_names": pack_tools,
                "show_in_chat": manifest.show_in_chat,
                "is_builtin": False,
            }

        try:
            profile = AgentProfileGuardrail.validate(data, available_tools=self.available_tools)
        except AgentValidationError as exc:
            raise ValueError(str(exc)) from exc

        if existing is not None and existing.is_builtin:
            if self.store is None:
                raise ValueError("State store is required to update a built-in agent from a pack.")
            self.store.save_agent_override(
                AgentCustomization(
                    agent_id=profile.id,
                    tone=profile.tone.value if hasattr(profile.tone, "value") else str(profile.tone),
                    system_prompt=profile.system_prompt,
                    model=profile.model,
                    purpose=profile.purpose.value if hasattr(profile.purpose, "value") else str(profile.purpose),
                    allowed_tool_names=profile.allowed_tool_names,
                    allowed_skill=profile.allowed_skill,
                    pack_tool_names=profile.pack_tool_names,
                    show_in_chat=profile.show_in_chat,
                    max_turns=profile.max_turns,
                    history_retention_days=profile.history_retention_days,
                )
            )
        else:
            self.agent_registry.register_custom_agent(profile)
        loaded = self.agent_registry.get_agent(profile.id)
        return loaded or profile


def _zip_dir(folder: Path, zip_path: Path) -> None:
    tmp = zip_path.with_suffix(zip_path.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue
            if _is_python_or_binary_tool(path):
                continue
            zf.write(path, path.relative_to(folder).as_posix())
    tmp.replace(zip_path)


def _extract_pack_zip(zip_path: Path, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if name.endswith("/") or ".." in Path(name).parts:
                continue
            suffix = Path(name).suffix.lower()
            if suffix in SKIP_PACK_SUFFIXES:
                continue
            target = dest / name
            if not str(target.resolve()).startswith(str(dest.resolve())):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info, "r") as src, target.open("wb") as out:
                out.write(src.read())
    pack_json = dest / "pack.json"
    if pack_json.is_file():
        return dest
    children = [p for p in dest.iterdir() if p.is_dir()]
    for child in children:
        if (child / "pack.json").is_file():
            return child
    raise ValueError("Zip does not contain pack.json.")
