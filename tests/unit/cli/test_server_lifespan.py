"""
Integration test for server lifespan and background scheduler execution [REQ-DEPLOY-006].
"""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


def test_server_lifespan_starts_and_stops_scheduler():
    store = SQLiteStateStore(":memory:")
    store.initialize_db()

    app = create_app(state_store=store, wiki_path="./data/test_wiki")

    # Verify that lifespan is configured on the FastAPI app
    assert app.router.lifespan_context is not None

    with (
        patch("src.application.routines.scheduler.RoutineScheduler.start", new_callable=AsyncMock) as mock_start,
        patch("src.application.routines.scheduler.RoutineScheduler.stop") as mock_stop,
    ):
        with TestClient(app) as client:
            resp = client.get("/api/agents")
            assert resp.status_code == 200
            # Scheduler start was called on startup
            assert mock_start.called

        # Scheduler stop was called on shutdown
        assert mock_stop.called
