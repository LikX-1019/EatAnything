import pytest
from pydantic import ValidationError

from app.core.errors import ApiError
from app.schemas.reviews import ReviewUpsertRequest
from app.schemas.stores import AdminStoreCreateRequest, AdminStoreUpdateRequest, RandomStoreRequest
from app.services.stores import attach_image


def test_store_code_is_normalized_and_validated() -> None:
    payload = AdminStoreCreateRequest(
        storeCode="  VALID_store-1  ",
        schoolId=1,
        areaId=1,
        name=" Test Store ",
        category=" Noodles ",
        address=" Main Street ",
    )

    assert payload.store_code == "valid_store-1"
    assert payload.name == "Test Store"
    assert payload.category == "Noodles"
    assert payload.address == "Main Street"

    with pytest.raises(ValidationError):
        AdminStoreCreateRequest(
            storeCode="invalid code!",
            schoolId=1,
            areaId=1,
            name="Test Store",
            category="Noodles",
            address="Main Street",
        )


@pytest.mark.parametrize("field", ["name", "category", "address"])
def test_store_create_rejects_blank_required_text(field: str) -> None:
    data = {
        "storeCode": "valid-store",
        "schoolId": 1,
        "areaId": 1,
        "name": "Test Store",
        "category": "Noodles",
        "address": "Main Street",
        field: "   ",
    }

    with pytest.raises(ValidationError):
        AdminStoreCreateRequest(**data)


def test_store_update_requires_an_actual_change() -> None:
    with pytest.raises(ValidationError):
        AdminStoreUpdateRequest(version=1)


def test_random_store_request_accepts_camel_case_school_id() -> None:
    payload = RandomStoreRequest(schoolId="9", excludeStoreId="12")

    assert payload.school_id == 9
    assert payload.exclude_store_id == "12"

    with pytest.raises(ValidationError):
        RandomStoreRequest(schoolId=0)


def test_review_rejects_blank_content() -> None:
    with pytest.raises(ValidationError):
        ReviewUpsertRequest(rating=5, content="   ")


@pytest.mark.parametrize("rating", [0, 6])
def test_review_rejects_rating_outside_one_to_five(rating: int) -> None:
    with pytest.raises(ValidationError):
        ReviewUpsertRequest(rating=rating, content="味道不错")


def test_review_rejects_content_over_backend_limit() -> None:
    with pytest.raises(ValidationError):
        ReviewUpsertRequest(rating=5, content="好" * 501)


@pytest.mark.asyncio
async def test_store_image_must_come_from_configured_storage() -> None:
    class Storage:
        public_url = "https://assets.example.com/media"
        bucket = "stores"

    with pytest.raises(ApiError) as error:
        await attach_image(
            session=None,  # type: ignore[arg-type]
            store=None,  # type: ignore[arg-type]
            image_url="https://untrusted.example/stores/image.jpg",
            storage=Storage(),  # type: ignore[arg-type]
        )

    assert error.value.code == "MEDIA_NOT_FOUND"
