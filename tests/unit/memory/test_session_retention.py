"""
Session retention prune [REQ-RET-002, REQ-RET-003].
"""

from src.domain.gateway.models import ChatMessage, Role
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def _backdate(store: SQLiteStateStore, session_id: str, when: str) -> None:
    conn = store._get_connection()
    try:
        conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (when, session_id))
        conn.commit()
    finally:
        if store._mem_conn is None:
            conn.close()


def test_prune_deletes_old_sessions_and_keeps_facts():
    store = SQLiteStateStore(db_path=":memory:")
    old = store.create_session(agent_id="assistant", title="Old chat")
    new = store.create_session(agent_id="assistant", title="New chat")
    store.save_message(old.id, "assistant", ChatMessage(role=Role.USER, content="hello old"))
    store.save_fact(entity="user", key="name", value="Jacob", source_session_id=old.id)
    _backdate(store, old.id, "2020-01-01T00:00:00+00:00")

    deleted = store.prune_expired_sessions(agent_id="assistant", max_age_days=30)
    assert deleted == 1
    assert store.get_session(old.id) is None
    assert store.get_session(new.id) is not None
    assert store.get_messages(old.id) == []
    conn = store._get_connection()
    try:
        n = conn.execute("SELECT COUNT(*) AS c FROM episodic_facts").fetchone()["c"]
    finally:
        if store._mem_conn is None:
            conn.close()
    assert n == 1


def test_prune_zero_days_never_deletes():
    store = SQLiteStateStore(db_path=":memory:")
    sess = store.create_session(agent_id="assistant", title="Keep")
    _backdate(store, sess.id, "2020-01-01T00:00:00+00:00")
    deleted = store.prune_expired_sessions(agent_id="assistant", max_age_days=0)
    assert deleted == 0
    assert store.get_session(sess.id) is not None


def test_prune_skips_excluded_session():
    store = SQLiteStateStore(db_path=":memory:")
    open_sess = store.create_session(agent_id="assistant", title="Open")
    _backdate(store, open_sess.id, "2020-01-01T00:00:00+00:00")
    deleted = store.prune_expired_sessions(
        agent_id="assistant",
        max_age_days=30,
        exclude_session_id=open_sess.id,
    )
    assert deleted == 0
    assert store.get_session(open_sess.id) is not None
