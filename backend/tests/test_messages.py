from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.core.errors import ApiError
from app.models import PlatformMessage
from app.services.messages import create_system_message, message_state, sanitize_message_html, validate_action
from app.workers import notifications as notification_worker


class MessageSession:
    def __init__(self):
        self.items = []

    def add(self, value):
        self.items.append(value)


def settings():
    return SimpleNamespace(minio_public_url="https://media.example.test")


def test_message_html_keeps_platform_images_and_removes_scripts() -> None:
    value = sanitize_message_html(
        '<h2>更新</h2><script>alert(1)</script><img src="https://media.example.test/bucket/a.png" onerror="x">',
        settings(),
    )
    assert "script" not in value
    assert "onerror" not in value
    assert "https://media.example.test/bucket/a.png" in value


def test_message_html_rejects_external_images() -> None:
    with pytest.raises(ApiError) as error:
        sanitize_message_html('<p>正文</p><img src="https://outside.example/a.png">', settings())
    assert error.value.code == "MESSAGE_IMAGE_INVALID"


def test_message_lifecycle_state_is_derived_from_time() -> None:
    now = datetime.now(UTC)
    item = PlatformMessage(status="published", publish_at=now + timedelta(minutes=1), expire_at=None)
    assert message_state(item, now) == "scheduled"
    item.publish_at = now - timedelta(minutes=2)
    assert message_state(item, now) == "active"
    item.expire_at = now - timedelta(minutes=1)
    assert message_state(item, now) == "expired"


def test_controlled_action_requires_store_id_only_for_detail() -> None:
    validate_action("reviews", None)
    validate_action("store_detail", 12)
    with pytest.raises(ApiError):
        validate_action("store_detail", None)
    with pytest.raises(ApiError):
        validate_action("https://example.com", None)


@pytest.mark.asyncio
async def test_system_message_joins_callers_transaction() -> None:
    session = MessageSession()
    item = await create_system_message(
        session, user_id=7, event_type="review.created", title="评价发布成功",
        body="正文 <script> 不会作为 HTML 执行", action_type="reviews",
    )
    assert session.items == [item]
    assert item.status == "published"
    assert "&lt;script&gt;" in item.body_html


def test_worker_builds_two_template_payload_without_html(monkeypatch) -> None:
    monkeypatch.setattr(
        notification_worker,
        "settings",
        SimpleNamespace(
            app_timezone="Asia/Shanghai",
            wechat_template=lambda kind: (f"{kind}-template", "thing1", "thing2", "time3"),
        ),
    )
    item = SimpleNamespace(
        kind="announcement", title="重要公告", body_html="<p>请及时查看<strong>最新安排</strong></p>",
        publish_at=datetime(2026, 8, 28, 4, 0, tzinfo=UTC), created_at=datetime.now(UTC),
    )
    template_id, data = notification_worker.template_data(item) or (None, {})
    assert template_id == "announcement-template"
    assert data["thing2"]["value"] == "请及时查看 最新安排"
    assert data["time3"]["value"] == "2026-08-28 12:00"
