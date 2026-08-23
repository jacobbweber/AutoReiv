"""
Unit tests for Mobile-First Responsive Layout & Viewport Overhaul [REQ-RESP-001, REQ-RESP-002, REQ-RESP-003].
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.web.app import create_app


@pytest.mark.asyncio
async def test_mobile_responsive_html_classes():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/")
        assert resp.status_code == 200
        html = resp.text

        # [REQ-RESP-001] Check 100dvh root layout classes
        assert "h-[100dvh]" in html or "h-dvh" in html

        # [REQ-RESP-001] Check sticky bottom chat input container
        assert "chatInputWrapper" in html or "sticky bottom-0" in html

        # [REQ-RESP-002] Check mobile drawer buttons in Wiki and Docs
        assert "wikiMobileDrawerBtn" in html
        assert "docsMobileDrawerBtn" in html

        # [REQ-RESP-003] Check responsive modal sheet classes
        assert "wikiMindMapModal" in html
