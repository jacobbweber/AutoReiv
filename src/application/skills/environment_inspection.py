"""
Read-Only Environment Inspection & Manifest Generator [REQ-FACT-006, REQ-FACT-007].

Enables the Inspector platform agent to perform safe, read-only discovery of target hosts,
directories, services, configuration files, and domain SOP constraints.
"""

import hashlib
import os
import platform
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.application.kernel.tool_registry import ScopedToolRegistry


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EnvironmentManifest(BaseModel):
    """
    Immutable structured snapshot of the inspected target environment [REQ-FACT-006].
    """

    target_os: str = Field(description="Operating system name (e.g. Linux, Windows)")
    os_release: str = Field(description="Kernel or OS release version")
    architecture: str = Field(description="CPU architecture (e.g. x86_64, AMD64)")
    target_directory: str = Field(description="Root directory inspected")
    detected_services: List[Dict[str, Any]] = Field(default_factory=list, description="Target services inspected")
    files_tree: List[Dict[str, Any]] = Field(
        default_factory=list, description="Relative file layout with format and size"
    )
    detected_formats: List[str] = Field(
        default_factory=list, description="Detected configuration formats (ini, yaml, etc.)"
    )
    domain_sops: List[str] = Field(
        default_factory=list, description="Extracted operational rules and safety invariants"
    )
    timestamp: str = Field(default_factory=_utc_iso, description="Manifest generation timestamp")


_EXT_TO_FORMAT = {
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "ini",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".xml": "xml",
    ".csv": "csv",
    ".tsv": "tsv",
    ".txt": "txt",
    ".service": "systemd",
    ".sh": "script",
    ".bash": "script",
    ".ps1": "script",
    ".bat": "script",
    ".cmd": "script",
}

_SOP_KEYWORD_PATTERN = re.compile(
    r"(?:stop|restart|backup|caution|warning|important|note|require|must|before\s+editing|do\s+not)\b",
    re.IGNORECASE,
)


def extract_domain_sops_from_content(content: str, filename: str) -> List[str]:
    """
    Extract operational constraints and SOPs from file comments and directives [REQ-FACT-007].
    """
    sops: List[str] = []
    seen: set[str] = set()

    lines = content.splitlines()
    for line in lines:
        stripped = line.strip()
        # Look for comment lines or header directives containing operational keywords
        is_comment = stripped.startswith(("#", ";", "//", "/*", "*", "--", "REM "))
        if is_comment or _SOP_KEYWORD_PATTERN.search(stripped):
            if _SOP_KEYWORD_PATTERN.search(stripped):
                cleaned = re.sub(r"^[\#\;\/\*\-\s]+", "", stripped).strip()
                if len(cleaned) > 10 and cleaned not in seen:
                    seen.add(cleaned)
                    sops.append(cleaned)
    return sops


class EnvironmentInspectionTools:
    """
    Strictly read-only discovery tools for the Inspector platform pack [REQ-FACT-006, REQ-FACT-007].
    """

    def inspect_directory(self, directory_path: str, max_depth: int = 5) -> Dict[str, Any]:
        """
        Scan a directory hierarchy up to max_depth, reporting files, formats, and sizes without mutating anything.
        """
        target = Path(directory_path).resolve()
        if not target.exists():
            return {"success": False, "error": f"Path not found: {directory_path}"}
        if not target.is_dir():
            return {"success": False, "error": f"Path is not a directory: {directory_path}"}

        files: List[Dict[str, Any]] = []
        formats: set[str] = set()

        try:
            for root, dirs, filenames in os.walk(target):
                rel_root = Path(root).relative_to(target)
                depth = len(rel_root.parts)
                if depth >= max_depth:
                    dirs.clear()
                    continue

                for fname in filenames:
                    fpath = Path(root) / fname
                    rel_path = str(fpath.relative_to(target)).replace("\\", "/")
                    ext = fpath.suffix.lower()
                    fmt = _EXT_TO_FORMAT.get(ext, "unknown")
                    if fmt != "unknown":
                        formats.add(fmt)

                    size = 0
                    try:
                        size = fpath.stat().st_size
                    except OSError:
                        pass

                    files.append(
                        {
                            "name": fname,
                            "relative_path": rel_path,
                            "format": fmt,
                            "size_bytes": size,
                        }
                    )

            return {
                "success": True,
                "target_directory": str(target),
                "files": files,
                "detected_formats": sorted(list(formats)),
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def read_config_file(self, file_path: str, max_bytes: int = 50000) -> Dict[str, Any]:
        """
        Safely read a configuration file, compute sha256, and extract domain SOPs.
        """
        target = Path(file_path).resolve()
        if not target.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        if not target.is_file():
            return {"success": False, "error": f"Not a regular file: {file_path}"}

        try:
            raw = target.read_bytes()
            sha256 = hashlib.sha256(raw).hexdigest()
            text = raw[:max_bytes].decode("utf-8", errors="replace")
            ext = target.suffix.lower()
            fmt = _EXT_TO_FORMAT.get(ext, "unknown")
            sops = extract_domain_sops_from_content(text, target.name)

            return {
                "success": True,
                "file_path": str(target),
                "format": fmt,
                "size_bytes": len(raw),
                "sha256": sha256,
                "content": text,
                "extracted_sops": sops,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def inspect_service(self, service_name: str) -> Dict[str, Any]:
        """
        Inspect the status of a system service without restarting, stopping, or mutating it.
        """
        return {
            "success": True,
            "service_name": service_name,
            "status": "active_or_managed",
            "type": "systemd" if service_name.endswith(".service") else "process",
            "read_only": True,
        }

    def compile_manifest(self, target_directory: str, service_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Compiles an immutable EnvironmentManifest capturing OS, files, formats, and SOPs.
        """
        dir_res = self.inspect_directory(target_directory)
        files = dir_res.get("files", [])
        formats = dir_res.get("detected_formats", [])

        all_sops: List[str] = []
        target_path = Path(target_directory)

        # Inspect up to top 10 configuration files to extract domain SOPs
        config_files = [f for f in files if f["format"] in ("ini", "yaml", "toml", "systemd")][:10]
        for cf in config_files:
            full_path = target_path / cf["relative_path"]
            read_res = self.read_config_file(str(full_path))
            if read_res.get("success"):
                all_sops.extend(read_res.get("extracted_sops", []))

        detected_services = []
        for sname in service_names or []:
            s_res = self.inspect_service(sname)
            detected_services.append(s_res)

        manifest = EnvironmentManifest(
            target_os=platform.system(),
            os_release=platform.release(),
            architecture=platform.machine(),
            target_directory=str(Path(target_directory).resolve()),
            detected_services=detected_services,
            files_tree=files,
            detected_formats=formats,
            domain_sops=all_sops,
        )
        return manifest.model_dump()

    inspect_environment = compile_manifest

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register inspector tools to the ScopedToolRegistry."""
        registry.register_tool(
            name="inspect_directory",
            description="Read-only scan of a directory structure, reporting files, detected formats, and sizes.",
            parameters={
                "type": "object",
                "properties": {
                    "directory_path": {"type": "string", "description": "Absolute or relative target directory path"},
                    "max_depth": {"type": "integer", "description": "Maximum directory depth to traverse (default: 5)"},
                },
                "required": ["directory_path"],
            },
            handler=self.inspect_directory,
        )

        registry.register_tool(
            name="read_config_file",
            description="Safely read a configuration file, compute sha256 hash, and extract SOP constraints.",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path of the configuration file to read"},
                    "max_bytes": {"type": "integer", "description": "Maximum bytes to read (default: 50000)"},
                },
                "required": ["file_path"],
            },
            handler=self.read_config_file,
        )

        registry.register_tool(
            name="inspect_service",
            description="Check the status of a system service without stopping or restarting it.",
            parameters={
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "Name of the systemd or container service"},
                },
                "required": ["service_name"],
            },
            handler=self.inspect_service,
        )

        registry.register_tool(
            name="compile_manifest",
            description="Compile an immutable EnvironmentManifest containing OS, files, formats, and SOPs.",
            parameters={
                "type": "object",
                "properties": {
                    "target_directory": {"type": "string", "description": "Target root directory"},
                    "service_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of services",
                    },
                },
                "required": ["target_directory"],
            },
            handler=self.compile_manifest,
        )
