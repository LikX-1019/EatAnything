import pytest

from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_round_trip() -> None:
    password_hash = hash_password("StrongPass123!")
    assert verify_password("StrongPass123!", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_jwt_round_trip() -> None:
    settings = get_settings()
    token = create_access_token(settings, subject="42", kind="user")
    payload = decode_access_token(settings, token)
    assert payload["sub"] == "42"
    assert payload["kind"] == "user"


def test_invalid_jwt_is_rejected() -> None:
    with pytest.raises(ApiError) as error:
        decode_access_token(get_settings(), "not-a-token")
    assert error.value.status_code == 401
    assert error.value.code == "AUTH_REQUIRED"
