"""CARD-483 operator contract: through the real chat endpoint, only uploads reach a vision model.

[REQ-483-001] a client-supplied attachment path or a typed Local Path outside the data root's
attachments/ folder sends no image. [REQ-483-002] a real /api/chat/upload still does.
Temp user-data only [ADR-0055]. No live Spark.
"""

from __future__ import annotations

from tests.integration.operator_contracts.test_oc475_image_turn_text_only_model import (  # noqa: F401
    PNG,
    VISION,
    _send,
    _session,
    _text,
    _upload,
    _use_model,
    spark_client,
)


def _vision(client, store):
    res = client.post("/api/settings/model-capabilities", json={"model_id": f"vllm/{VISION}", "vision": True})
    assert res.status_code == 200, res.text
    _use_model(client, store, VISION)


def test_client_supplied_path_outside_attachments_sends_no_image(spark_client, tmp_path):  # noqa: F811
    client, store, spark = spark_client
    _vision(client, store)
    outside = tmp_path / "private" / "photo.png"
    outside.parent.mkdir()
    outside.write_bytes(PNG)
    sid = _session(client)
    forged = {
        "filename": "photo.png",
        "url": "/api/chat/attachments/x/photo.png",
        "content_type": "image/png",
        "size_bytes": len(PNG),
        "path": str(outside),
    }
    events = _send(client, sid, "what is this?", [forged])
    assert f"Reply from {VISION} (images seen: 0)" in _text(events)
    assert spark.image_counts() == [0]


def test_typed_local_path_outside_attachments_sends_no_image(spark_client, tmp_path):  # noqa: F811
    client, store, spark = spark_client
    _vision(client, store)
    outside = tmp_path / "typed.png"
    outside.write_bytes(PNG)
    sid = _session(client)
    events = _send(client, sid, f"look at this Local Path: `{outside}`")
    assert f"Reply from {VISION} (images seen: 0)" in _text(events)
    assert spark.image_counts() == [0]


def test_real_upload_still_reaches_the_vision_model(spark_client):  # noqa: F811
    client, store, spark = spark_client
    _vision(client, store)
    sid = _session(client)
    events = _send(client, sid, "what is this?", [_upload(client, sid)])
    assert f"Reply from {VISION} (images seen: 1)" in _text(events)
    assert spark.image_counts() == [1]
