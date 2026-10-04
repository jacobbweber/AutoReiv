"""CARD-483: images are only read from the attachments folder.

[REQ-483-001] an image path outside the data root's attachments/ folder (typed, client-supplied,
or reached with ..) is never sent to a model.
[REQ-483-002] an upload in the attachments folder is still attached (CARD-475 unchanged).
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

import pytest

from src.application.gateway.attachment_images import (
    current_turn_images,
    inside_attachments_dir,
    prepare_image_turn,
)
from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.model_capabilities import OVERRIDES_SETTING, ModelCapabilityResolver
from src.domain.gateway.models import ChatMessage, CompletionRequest, Role
from tests.unit.gateway.test_image_turn_gating_475 import RecordingProvider

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
VISION = "gemma-4-26b-a4b"


def _png(folder: Path, name: str = "abc123_shot.png") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / name
    p.write_bytes(PNG)
    return p


def _turn(path, name: str = "shot.png") -> str:
    return (
        f"what is this?\n\n---\n![{name}](/api/chat/attachments/abc123/{name})\n"
        f"*(Attached Image: `{name}`, {len(PNG)} bytes, format: `image/png`, Local Path: `{path}`)*"
    )


@pytest.fixture
def dirs(tmp_path):
    att = tmp_path / "data" / "attachments"
    att.mkdir(parents=True)
    return att, tmp_path / "elsewhere"


def test_upload_inside_the_attachments_folder_is_attached(dirs):
    att, _ = dirs
    up = _png(att / "session-1")
    images = current_turn_images(_turn(up), att)
    assert [(i["filename"], Path(i["path"])) for i in images] == [("shot.png", up.resolve())]


def test_image_outside_the_attachments_folder_is_not_attached(dirs):
    att, elsewhere = dirs
    assert current_turn_images(_turn(_png(elsewhere)), att) == []


def test_a_typed_local_path_outside_the_folder_is_not_attached(dirs):
    att, elsewhere = dirs
    other = _png(elsewhere, "holiday.jpg")
    assert current_turn_images(f"please look at Local Path: `{other}`", att) == []


def test_dot_dot_out_of_the_folder_is_not_attached(dirs):
    att, elsewhere = dirs
    other = _png(elsewhere)
    sneaky = att / "session-1" / ".." / ".." / ".." / "elsewhere" / other.name
    assert sneaky.exists()
    assert current_turn_images(_turn(sneaky), att) == []


def test_a_sibling_folder_with_the_same_prefix_is_outside(dirs):
    att, _ = dirs
    sibling = _png(att.parent / "attachments-old")
    assert current_turn_images(_turn(sibling), att) == []


def test_no_attachments_folder_attaches_nothing(dirs):
    att, _ = dirs
    up = _png(att)
    assert current_turn_images(_turn(up)) == []
    assert current_turn_images(_turn(up), lambda: None) == []


def test_folder_may_be_given_lazily_and_is_only_resolved_when_a_path_is_named(dirs):
    att, _ = dirs
    calls = []

    def resolver():
        calls.append(1)
        return att

    assert current_turn_images("hello, no attachments here", resolver) == []
    assert calls == []
    assert len(current_turn_images(_turn(_png(att)), resolver)) == 1
    assert calls == [1]


def test_a_failing_resolver_attaches_nothing(dirs):
    att, _ = dirs

    def broken():
        raise RuntimeError("no data root")

    assert current_turn_images(_turn(_png(att)), broken) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows paths are case-insensitive")
def test_windows_case_differences_still_match(dirs):
    att, _ = dirs
    up = _png(att)
    assert len(current_turn_images(_turn(str(up).upper()), att)) == 1


def test_inside_attachments_dir_helper(dirs):
    att, elsewhere = dirs
    root = os.path.normcase(str(att.resolve()))
    assert inside_attachments_dir(_png(att), root) is not None
    assert inside_attachments_dir(_png(elsewhere), root) is None
    assert inside_attachments_dir(att / "missing.png", root) is None
    assert inside_attachments_dir(_png(att), None) is None


def test_prepare_image_turn_skips_outside_paths_without_a_note(dirs):
    att, elsewhere = dirs
    msgs = [ChatMessage(role=Role.USER, content=_turn(_png(elsewhere)))]
    out, dropped, attached = prepare_image_turn(msgs, can_view_images=False, attachments_dir=att)
    assert (dropped, attached) == (None, False)
    assert out[0].content == msgs[0].content  # treated as missing: no 'cannot view images' note


def _vision_gateway(provider, attachments_dir=None):
    gw = MultiProviderGateway()
    gw.register_provider(provider)
    settings = {OVERRIDES_SETTING: {f"vllm/{VISION}": True}}
    gw.set_capability_resolver(ModelCapabilityResolver(settings_getter=lambda k, d=None: settings.get(k, d)))
    if attachments_dir is not None:
        gw.set_attachments_dir_resolver(lambda: attachments_dir)
    return gw


@pytest.mark.asyncio
async def test_gateway_sends_uploads_but_not_outside_files_to_a_vision_model(dirs):
    att, elsewhere = dirs
    provider = RecordingProvider()
    gw = _vision_gateway(provider, att)
    await gw.complete(
        CompletionRequest(model=f"vllm/{VISION}", messages=[ChatMessage(role=Role.USER, content=_turn(_png(att)))])
    )
    await gw.complete(
        CompletionRequest(
            model=f"vllm/{VISION}", messages=[ChatMessage(role=Role.USER, content=_turn(_png(elsewhere)))]
        )
    )
    sent = [bool(r.messages[-1].images) for r in provider.requests]
    assert sent == [True, False]


@pytest.mark.asyncio
async def test_gateway_without_an_attachments_folder_sends_no_images(dirs):
    att, _ = dirs
    provider = RecordingProvider()
    gw = _vision_gateway(provider)
    await gw.complete(
        CompletionRequest(model=f"vllm/{VISION}", messages=[ChatMessage(role=Role.USER, content=_turn(_png(att)))])
    )
    assert not provider.requests[-1].messages[-1].images


def test_app_wires_the_upload_folder():
    src = Path(__file__).resolve().parents[3].joinpath("src/web/app.py").read_text(encoding="utf-8")
    assert "set_attachments_dir_resolver(_attachments_dir)" in src
    assert 'Path(paths.root) / "attachments"' in src
