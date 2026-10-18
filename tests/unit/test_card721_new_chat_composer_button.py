"""CARD-721 guard: #newChatBtn sits in #chatForm to the left of #chatOptionsToggleBtn, not inside #chatOptionsDrawer."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.guard

REPO_ROOT = Path(__file__).resolve().parents[2]
CHAT_HTML = REPO_ROOT / "src" / "web" / "templates" / "partials" / "chat.html"
DESKTOP_CSS = REPO_ROOT / "src" / "web" / "static" / "css" / "desktop.css"


def test_new_chat_btn_is_in_composer_left_of_options_and_not_in_drawers():
    html = CHAT_HTML.read_text(encoding="utf-8")

    # Exactly one #newChatBtn in chat.html
    assert html.count('id="newChatBtn"') == 1

    # Not inside #chatSessionsDrawer
    sessions_start = html.index('id="chatSessionsDrawer"')
    sessions_end = html.index("</aside>", sessions_start)
    assert 'id="newChatBtn"' not in html[sessions_start:sessions_end]

    # Not inside #chatOptionsDrawer (which precedes #chatForm)
    options_drawer_start = html.index('id="chatOptionsDrawer"')
    chat_form_start = html.index('id="chatForm"')
    assert options_drawer_start < chat_form_start
    assert 'id="newChatBtn"' not in html[options_drawer_start:chat_form_start]
    assert 'data-card="466"' not in html[options_drawer_start:chat_form_start]

    # Inside #chatForm, immediately to the left of #chatOptionsToggleBtn
    new_chat_idx = html.index('id="newChatBtn"')
    options_toggle_idx = html.index('id="chatOptionsToggleBtn"')
    send_btn_idx = html.index('id="sendBtn"')
    assert chat_form_start < new_chat_idx < options_toggle_idx < send_btn_idx

    # Uses plus icon and "+ New" label
    new_chat_slice = html[new_chat_idx : options_toggle_idx]
    assert 'data-lucide="plus"' in new_chat_slice
    assert ">New<" in new_chat_slice


def test_desktop_css_includes_new_chat_btn_in_hosted_pointer_events():
    css = DESKTOP_CSS.read_text(encoding="utf-8")
    assert "#view-chat.desktop-view-hosted #newChatBtn" in css
