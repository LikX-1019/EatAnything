import pytest

from app.core.config import get_settings
from app.core.errors import ApiError
from app.services.import_stores import parse_rows


@pytest.mark.asyncio
async def test_parse_valid_csv() -> None:
    content = (
        "storeCode,schoolCode,areaCode,name,category,address,imageUrl,status\n"
        "test-store,wtbu,south-canteen,测试店,测试,测试路1号,,hidden\n"
    ).encode("utf-8")
    rows = await parse_rows(content, "stores.csv", get_settings())
    assert rows[0]["storeCode"] == "test-store"
    assert rows[0]["schoolCode"] == "wtbu"
    assert rows[0]["areaCode"] == "south-canteen"
    assert rows[0]["status"] == "hidden"


@pytest.mark.asyncio
async def test_duplicate_store_code_is_rejected() -> None:
    content = (
        "storeCode,schoolCode,areaCode,name,category,address,imageUrl,status\n"
        "same-store,wtbu,south-canteen,测试店,测试,测试路1号,,hidden\n"
        "SAME-STORE,wtbu,north-canteen,测试店2,测试,测试路2号,,hidden\n"
    ).encode("utf-8")
    with pytest.raises(ApiError) as error:
        await parse_rows(content, "stores.csv", get_settings())
    assert error.value.status_code == 422
    assert any(item["code"] == "DUPLICATE_STORE_CODE_IN_FILE" for item in error.value.details)


@pytest.mark.asyncio
async def test_invalid_status_is_rejected() -> None:
    content = (
        "storeCode,schoolCode,areaCode,name,category,address,imageUrl,status\n"
        "test-store,wtbu,south-canteen,测试店,测试,测试路1号,,published\n"
    ).encode("utf-8")
    with pytest.raises(ApiError) as error:
        await parse_rows(content, "stores.csv", get_settings())
    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_parse_school_scoped_chinese_template() -> None:
    content = (
        "食堂,店铺位置,店铺名称,店铺图片\n"
        "南食堂,一楼 A 区,测试店铺,https://example.com/store.jpg\n"
    ).encode("utf-8")
    rows = await parse_rows(content, "stores.csv", get_settings(), target_school_id=1)
    assert rows[0]["areaName"] == "南食堂"
    assert rows[0]["address"] == "一楼 A 区"
    assert rows[0]["name"] == "测试店铺"
    assert rows[0]["imageUrl"] == "https://example.com/store.jpg"
