"""CARD-731 / ADR-0067: Docker mounts the projects folder and ships a dev toolchain.

ADR-0067 makes projects user data: the serve resolves `AUTOREIV_PROJECTS_DIR`, else `<data root>/projects`.
In Docker that folder is `/data/projects`, mounted from the host like the wiki so the operator can open the same
folder in VS Code. Commands run where the serve runs, so the image carries the toolchains a project needs.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.guard

ROOT = Path(__file__).resolve().parents[3]
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")
COMPOSE = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
SERVICE = COMPOSE["services"]["autoreiv"]


def _runner_stage() -> str:
    """The final image stage, where the toolchain must live (not the throwaway builder)."""
    parts = re.split(r"(?m)^FROM\s+", DOCKERFILE)
    runner = [p for p in parts if re.match(r"\S+\s+AS\s+runner\b", p, re.I)]
    assert runner, "Dockerfile has a runner stage"
    return runner[0]


def test_compose_mounts_projects_folder_from_host_path_or_named_volume():
    volumes = SERVICE["volumes"]
    assert "${AUTOREIV_PROJECTS_HOST_PATH:-autoreiv-projects}:/data/projects" in volumes
    assert "autoreiv-projects" in COMPOSE["volumes"]


def test_compose_sets_projects_dir_and_passes_github_token():
    env = SERVICE["environment"]
    assert "AUTOREIV_PROJECTS_DIR=/data/projects" in env
    assert "GITHUB_TOKEN=${GITHUB_TOKEN:-}" in env


def test_dockerfile_sets_projects_dir_and_creates_it_for_the_app_user():
    runner = _runner_stage()
    assert re.search(r"AUTOREIV_PROJECTS_DIR=/data/projects", runner)
    mkdir = [ln for ln in runner.splitlines() if "mkdir" in ln and not ln.lstrip().startswith("#")]
    assert any("/data/projects" in ln for ln in mkdir), mkdir
    # the wiki must stay un-created so the ADR-0056 hard-fail still fires when it is not mounted
    assert not any("/data/wiki" in ln for ln in mkdir), mkdir


def test_dockerfile_trusts_bind_mounted_repos_owned_by_host_uids():
    assert "safe.directory '*'" in _runner_stage()


def test_runner_stage_ships_node_npm_uv_make_and_gpp():
    runner = _runner_stage()
    assert re.search(r"COPY --from=node:22[^\s]*\s+/usr/local/bin/node\s", runner)
    assert "/usr/local/lib/node_modules" in runner
    for link in ("npm", "npx"):
        assert f"/usr/local/bin/{link}" in runner, link
    assert re.search(r"COPY --from=ghcr\.io/astral-sh/uv[^\s]*\s+/uv\b", runner)
    assert re.search(r"\bmake\b", runner) and re.search(r"\bg\+\+", runner)


def test_runner_stage_installs_godot_headless_behind_build_args():
    runner = _runner_stage()
    assert re.search(r"(?m)^ARG INSTALL_GODOT=1$", runner)
    assert re.search(r"(?m)^ARG GODOT_VERSION=4\.\d+(\.\d+)?$", runner)
    assert "TARGETARCH" in runner
    assert "/usr/local/bin/godot" in runner


def test_update_machinery_from_card722_is_kept():
    assert "COPY --chown=autoreiv:autoreiv .git/ ./.git/" in DOCKERFILE
    assert "git config --global --add safe.directory /app" in DOCKERFILE
    assert "git sparse-checkout set" in DOCKERFILE
    assert "'/platform/**'" in DOCKERFILE
    # templates/ is retired by CARD-729 (ADR-0067): neither copied nor checked out
    assert "templates/" not in DOCKERFILE and "'/templates/**'" not in DOCKERFILE
