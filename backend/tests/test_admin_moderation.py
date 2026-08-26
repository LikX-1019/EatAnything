from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.core.errors import ApiError
from app.services.moderation import (
    ensure_user_can_comment,
    ensure_user_can_upload_image,
    restriction_active,
)


class RestrictionSession:
    def __init__(self, restriction=None):
        self.restriction = restriction

    async def get(self, _model, _key):
        return self.restriction


def test_restriction_expiry_is_effective_without_background_job() -> None:
    assert restriction_active(True, None)
    assert restriction_active(True, datetime.now(UTC) + timedelta(minutes=1))
    assert not restriction_active(True, datetime.now(UTC) - timedelta(minutes=1))
    assert not restriction_active(False, None)


@pytest.mark.asyncio
async def test_comment_restriction_blocks_review_write() -> None:
    restriction = SimpleNamespace(comment_blocked=True, comment_blocked_until=None)
    with pytest.raises(ApiError) as error:
        await ensure_user_can_comment(RestrictionSession(restriction), 1)
    assert error.value.code == "COMMENT_BLOCKED"


@pytest.mark.asyncio
async def test_image_restriction_blocks_upload() -> None:
    restriction = SimpleNamespace(image_upload_blocked=True, image_upload_blocked_until=None)
    with pytest.raises(ApiError) as error:
        await ensure_user_can_upload_image(RestrictionSession(restriction), 1)
    assert error.value.code == "IMAGE_UPLOAD_BLOCKED"
