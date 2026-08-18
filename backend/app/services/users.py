from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.minio import MinioStorage
from app.repositories.users import user_stats


async def profile(session: AsyncSession, storage: MinioStorage, user) -> dict:
    avatar_url = None
    if user.avatar:
        avatar_url = storage.public_object_url(user.avatar.object_key)
    return {
        "id": str(user.id),
        "nickname": user.nickname,
        "avatar_url": avatar_url,
        "school_id": str(user.school_id) if user.school_id is not None else None,
        "school": (
            {
                "id": str(user.school.id),
                "school_code": user.school.school_code,
                "name": user.school.name,
                "city": user.school.city,
                "district": user.school.district,
                "address": user.school.address,
            }
            if user.school
            else None
        ),
        "slogan": user.slogan,
        "level": user.level,
        "stats": await user_stats(session, user.id),
        "created_at": user.created_at.isoformat(),
    }
