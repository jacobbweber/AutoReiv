"""
Unit tests for Platform Remote Tools and Security Guardrails [REQ-REMOTE-004, REQ-REMOTE-005].
"""

import io
from unittest.mock import MagicMock, patch

import pytest

from src.application.kernel.tool_registry import _tool_context
from src.application.skills.remote_tools import RemoteTools
from src.domain.remote.models import RemoteHost
from src.domain.security.vault import Credential
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store(tmp_path):
    s = SQLiteStateStore(db_path=str(tmp_path / "test.db"))
    # Save a credential
    s.save_credential(
        Credential(
            id="cred-vps-key",
            name="VPS Key",
            type="key",
            secret="super-secret-ssh-token",
        )
    )
    # Save a remote host
    s.save_remote_host(
        RemoteHost(
            id="srv-web",
            label="Web Server",
            host="10.0.0.10",
            port=22,
            username="deploy",
            credential_id="cred-vps-key",
        )
    )
    return s


@pytest.mark.asyncio
async def test_ssh_exec_command_success(store):
    tools = RemoteTools(store=store)

    # Set tool context for authorized agent
    token = _tool_context.set({
        "agent_id": "sysadmin",
        "allowed_credentials": ["cred-vps-key"],
        "credentials": {"cred-vps-key": "super-secret-ssh-token"},
    })
    try:
        with patch("paramiko.SSHClient") as mock_ssh:
            client_mock = MagicMock()
            mock_ssh.return_value = client_mock
            stdin_mock = MagicMock()
            stdout_mock = MagicMock()
            stderr_mock = MagicMock()

            stdout_mock.read.return_value = b"Linux web-01 6.1.0\n"
            stderr_mock.read.return_value = b""
            stdout_mock.channel.recv_exit_status.return_value = 0

            client_mock.exec_command.return_value = (stdin_mock, stdout_mock, stderr_mock)

            res = await tools.ssh_exec_command(host_id="srv-web", command="uname -a")
            assert res["exit_code"] == 0
            assert "Linux web-01" in res["stdout"]
            assert res["error"] is None
    finally:
        _tool_context.reset(token)


@pytest.mark.asyncio
async def test_ssh_exec_command_unauthorized_credential(store):
    tools = RemoteTools(store=store)

    # Agent is NOT granted cred-vps-key
    token = _tool_context.set({
        "agent_id": "unauthorized-agent",
        "allowed_credentials": ["other-cred"],
        "credentials": {"other-cred": "secret"},
    })
    try:
        res = await tools.ssh_exec_command(host_id="srv-web", command="ls -la")
        assert res["exit_code"] == -1
        assert "not authorized" in res["error"].lower()
    finally:
        _tool_context.reset(token)


@pytest.mark.asyncio
async def test_ssh_exec_command_dangerous_command_blocked(store):
    tools = RemoteTools(store=store)

    token = _tool_context.set({
        "agent_id": "sysadmin",
        "allowed_credentials": ["cred-vps-key"],
        "credentials": {"cred-vps-key": "super-secret-ssh-token"},
    })
    try:
        res = await tools.ssh_exec_command(host_id="srv-web", command="rm -rf / --no-preserve-root")
        assert res["exit_code"] == -1
        assert "dangerous" in res["error"].lower() or "prohibited" in res["error"].lower()
    finally:
        _tool_context.reset(token)


@pytest.mark.asyncio
async def test_ssh_read_file_success(store):
    tools = RemoteTools(store=store)

    token = _tool_context.set({
        "agent_id": "sysadmin",
        "allowed_credentials": ["cred-vps-key"],
        "credentials": {"cred-vps-key": "super-secret-ssh-token"},
    })
    try:
        with patch("paramiko.SSHClient") as mock_ssh:
            client_mock = MagicMock()
            mock_ssh.return_value = client_mock
            sftp_mock = MagicMock()
            client_mock.open_sftp.return_value = sftp_mock

            file_mock = io.BytesIO(b"server_name example.com;\nlisten 80;\n")
            sftp_mock.open.return_value.__enter__.return_value = file_mock

            res = await tools.ssh_read_file(host_id="srv-web", file_path="/etc/nginx/nginx.conf")
            assert res["success"] is True
            assert "server_name example.com;" in res["content"]
            assert res["file_path"] == "/etc/nginx/nginx.conf"
    finally:
        _tool_context.reset(token)


@pytest.mark.asyncio
async def test_ssh_inspect_environment_success(store):
    tools = RemoteTools(store=store)

    token = _tool_context.set({
        "agent_id": "sysadmin",
        "allowed_credentials": ["cred-vps-key"],
        "credentials": {"cred-vps-key": "super-secret-ssh-token"},
    })
    try:
        with patch("paramiko.SSHClient") as mock_ssh:
            client_mock = MagicMock()
            mock_ssh.return_value = client_mock

            def mock_exec(cmd, *args, **kwargs):
                stdout_mock = MagicMock()
                stderr_mock = MagicMock()
                stderr_mock.read.return_value = b""
                stdout_mock.channel.recv_exit_status.return_value = 0
                if "uname" in cmd:
                    stdout_mock.read.return_value = b"Linux srv-web 5.15.0 x86_64\n"
                elif "uptime" in cmd:
                    stdout_mock.read.return_value = b"up 10 days, 2 users, load average: 0.10, 0.05, 0.01\n"
                elif "df" in cmd:
                    stdout_mock.read.return_value = b"/dev/sda1  50G  20G  30G  40% /\n"
                else:
                    stdout_mock.read.return_value = b"ok\n"
                return MagicMock(), stdout_mock, stderr_mock

            client_mock.exec_command.side_effect = mock_exec

            res = await tools.ssh_inspect_environment(host_id="srv-web")
            assert res["success"] is True
            assert res["host_id"] == "srv-web"
            assert "Linux" in res["os"]
            assert "10 days" in res["uptime"]
            assert "/dev/sda1" in res["disk_usage"]
    finally:
        _tool_context.reset(token)
