"""
Unit tests for RemoteHost model and SQLite repository [REQ-REMOTE-001].
"""

import pytest

from src.domain.remote.models import RemoteHost
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "test_remote.db"
    return SQLiteStateStore(db_path=str(db_path))


def test_save_and_get_remote_host(store):
    host = RemoteHost(
        id="srv-game",
        label="Game Server",
        host="192.168.1.100",
        port=2222,
        username="steam",
        auth_type="password",
        credential_id="cred_steam_pw",
    )
    assert store.save_remote_host(host) is True

    fetched = store.get_remote_host("srv-game")
    assert fetched is not None
    assert fetched.id == "srv-game"
    assert fetched.label == "Game Server"
    assert fetched.host == "192.168.1.100"
    assert fetched.port == 2222
    assert fetched.username == "steam"
    assert fetched.auth_type == "password"
    assert fetched.credential_id == "cred_steam_pw"
    assert fetched.created_at is not None


def test_list_and_delete_remote_hosts(store):
    h1 = RemoteHost(id="host1", label="Alpha Host", host="10.0.0.1", username="root")
    h2 = RemoteHost(id="host2", label="Beta Host", host="10.0.0.2", username="admin")

    store.save_remote_host(h1)
    store.save_remote_host(h2)

    hosts = store.list_remote_hosts()
    assert len(hosts) == 2
    assert [h.id for h in hosts] == ["host1", "host2"]

    assert store.delete_remote_host("host1") is True
    assert store.get_remote_host("host1") is None
    assert len(store.list_remote_hosts()) == 1
