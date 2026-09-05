"""
Unit tests for Read-Only Environment Inspection & Manifest Generator [REQ-FACT-006, REQ-FACT-007].
"""

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.environment_inspection import (
    EnvironmentInspectionTools,
    EnvironmentManifest,
    extract_domain_sops_from_content,
)


@pytest.fixture
def mock_target_env(tmp_path):
    """Creates a simulated game server directory layout."""
    server_dir = tmp_path / "palworld_server"
    server_dir.mkdir(parents=True)
    config_dir = server_dir / "Config"
    config_dir.mkdir(parents=True)
    saves_dir = server_dir / "SaveGames"
    saves_dir.mkdir(parents=True)

    # 1. Config file (INI)
    ini_content = (
        "; PalWorldSettings.ini\n"
        "; IMPORTANT: Always stop the server before editing this file, or settings will be overwritten on shutdown!\n"
        "[ServerSettings]\n"
        'ServerName="My Dedicated Server"\n'
        "ServerPort=8211\n"
        'ServerPassword="secret123"\n'
        "AutoBackupMinutes=30\n"
    )
    (config_dir / "PalWorldSettings.ini").write_text(ini_content, encoding="utf-8")

    # 2. Docker compose / YAML file
    compose_content = (
        "version: '3.8'\n"
        "services:\n"
        "  palworld:\n"
        "    image: thies/palworld:latest\n"
        "    ports:\n"
        "      - '8211:8211/udp'\n"
        "    volumes:\n"
        "      - ./SaveGames:/palworld/SaveGames\n"
    )
    (server_dir / "docker-compose.yml").write_text(compose_content, encoding="utf-8")

    # 3. JSON status / state file
    (server_dir / "server_info.json").write_text('{"version": "v0.2.4", "players": 0}', encoding="utf-8")

    return server_dir


def test_inspect_directory_scans_files_and_detects_formats(mock_target_env):
    tools = EnvironmentInspectionTools()
    result = tools.inspect_directory(str(mock_target_env))
    assert result["success"] is True
    files = result["files"]
    assert len(files) >= 3

    formats = result["detected_formats"]
    assert "ini" in formats
    assert "yaml" in formats
    assert "json" in formats

    # Check relative paths and sizes
    names = {f["name"] for f in files}
    assert "PalWorldSettings.ini" in names
    assert "docker-compose.yml" in names
    assert "server_info.json" in names


def test_read_config_file_returns_content_and_hash(mock_target_env):
    tools = EnvironmentInspectionTools()
    ini_path = str(mock_target_env / "Config" / "PalWorldSettings.ini")
    result = tools.read_config_file(ini_path)

    assert result["success"] is True
    assert "ServerPort=8211" in result["content"]
    assert result["format"] == "ini"
    assert "sha256" in result
    assert len(result["sha256"]) == 64


def test_compile_environment_manifest(mock_target_env):
    tools = EnvironmentInspectionTools()
    manifest_dict = tools.compile_manifest(
        target_directory=str(mock_target_env),
        service_names=["palworld.service"],
    )

    manifest = EnvironmentManifest.model_validate(manifest_dict)
    assert manifest.target_directory == str(mock_target_env)
    assert len(manifest.files_tree) >= 3
    assert "ini" in manifest.detected_formats
    assert "yaml" in manifest.detected_formats
    assert manifest.target_os != ""
    assert len(manifest.domain_sops) >= 1
    # Verify extracted SOP contains shutdown rule from INI comment
    assert any("stop the server before editing" in sop.lower() for sop in manifest.domain_sops)


def test_domain_sop_extractor_heuristics():
    sample_text = (
        "# Standard Operating Procedure\n"
        "# WARNING: Stop daemon before altering config. Always backup data.tar.gz first.\n"
        "listen_port = 9000\n"
    )
    sops = extract_domain_sops_from_content(sample_text, "config.conf")
    assert len(sops) >= 1
    assert any("stop daemon before altering config" in sop.lower() for sop in sops)


def test_inspector_tools_register_in_scoped_registry():
    registry = ScopedToolRegistry()
    tools = EnvironmentInspectionTools()
    tools.register_tools(registry)

    tool_names = [t.name for t in registry.list_tools()]
    assert "inspect_directory" in tool_names
    assert "inspect_service" in tool_names
    assert "read_config_file" in tool_names
    assert "compile_manifest" in tool_names

    # Zero write/mutation tools
    for name in tool_names:
        assert not name.startswith("write_")
        assert not name.startswith("edit_")
        assert not name.startswith("delete_")
        assert not name.startswith("start_")
        assert not name.startswith("restart_")
