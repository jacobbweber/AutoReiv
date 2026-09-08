"""
Unit tests for AutoReiv Deploy Suite [CARD-193].
Validates deployment scripts, uninstallers, Dockerfile, and Compose manifests.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DEPLOY_DIR = REPO_ROOT / "deploy"


def test_systemd_deploy_suite_files():
    """Verify systemd service and both install/uninstall scripts exist."""
    service_file = DEPLOY_DIR / "systemd" / "autoreiv.service"
    install_script = DEPLOY_DIR / "systemd" / "install_systemd.sh"
    uninstall_script = DEPLOY_DIR / "systemd" / "uninstall_systemd.sh"

    assert service_file.is_file(), "autoreiv.service must exist"
    assert install_script.is_file(), "install_systemd.sh must exist"
    assert uninstall_script.is_file(), "uninstall_systemd.sh must exist"

    # Verify service unit uses canonical AUTOREIV_DATA_DIR
    service_content = service_file.read_text(encoding="utf-8")
    assert "AUTOREIV_DATA_DIR=/var/lib/autoreiv" in service_content
    assert "AUTOREIV_DB_PATH=" not in service_content
    assert "AUTOREIV_WIKI_PATH=" not in service_content

    # Verify install script syntax and directory handling
    install_content = install_script.read_text(encoding="utf-8")
    assert "set -euo pipefail" in install_content
    assert "templates" in install_content

    # Verify uninstaller script safety and features
    uninstall_content = uninstall_script.read_text(encoding="utf-8")
    assert "set -euo pipefail" in uninstall_content
    assert "systemctl stop autoreiv.service" in uninstall_content
    assert "systemctl disable autoreiv.service" in uninstall_content
    assert "--purge-data" in uninstall_content


def test_windows_deploy_suite_files():
    """Verify Windows runners and install/uninstall scripts exist."""
    install_script = DEPLOY_DIR / "windows" / "install_windows_service.ps1"
    uninstall_script = DEPLOY_DIR / "windows" / "uninstall_windows_service.ps1"
    run_ps1 = DEPLOY_DIR / "windows" / "run_autoreiv.ps1"
    run_bat = DEPLOY_DIR / "windows" / "run_autoreiv.bat"

    assert install_script.is_file(), "install_windows_service.ps1 must exist"
    assert uninstall_script.is_file(), "uninstall_windows_service.ps1 must exist"
    assert run_ps1.is_file(), "run_autoreiv.ps1 must exist"
    assert run_bat.is_file(), "run_autoreiv.bat must exist"

    uninstall_content = uninstall_script.read_text(encoding="utf-8")
    assert "Administrator" in uninstall_content
    assert "ServiceName" in uninstall_content
    assert "Stop-Service" in uninstall_content or "nssm stop" in uninstall_content


def test_dockerfile_templates_and_layout():
    """Verify Dockerfile copies templates and configures volume mount."""
    dockerfile = REPO_ROOT / "Dockerfile"
    assert dockerfile.is_file(), "Dockerfile must exist"
    content = dockerfile.read_text(encoding="utf-8")

    # Must copy templates directory for Developer Agent
    assert "COPY --chown=autoreiv:autoreiv templates/ ./templates/" in content
    assert "AUTOREIV_DATA_DIR=/data" in content
    assert "EXPOSE 8000" in content


def test_docker_compose_manifest():
    """Verify docker-compose.yml is valid YAML and modernized."""
    compose_file = REPO_ROOT / "docker-compose.yml"
    assert compose_file.is_file(), "docker-compose.yml must exist"
    raw_content = compose_file.read_text(encoding="utf-8")

    # Modern compose does not require or recommend top-level version
    parsed = yaml.safe_load(raw_content)
    assert "version" not in parsed, "Obsolete version key should be removed from compose manifest"
    assert "services" in parsed
    assert "autoreiv" in parsed["services"]
    svc = parsed["services"]["autoreiv"]
    assert "volumes" in svc
    assert any("autoreiv-data:/data" in v for v in svc["volumes"])


def test_deploy_readme_exists():
    """Verify deploy/README.md documentation exists and covers all environments."""
    readme_file = DEPLOY_DIR / "README.md"
    assert readme_file.is_file(), "deploy/README.md documentation must exist"
    content = readme_file.read_text(encoding="utf-8")
    assert "systemd" in content.lower()
    assert "windows" in content.lower()
    assert "docker" in content.lower()
    assert "uninstall" in content.lower()
