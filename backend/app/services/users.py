from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.minio import MinioStorage
from app.repositories.users import user_stats


async def profile(session: AsyncSession, storage: MinioStorage, user) -> dict:
    # 用户头像属于私有媒体；在提供鉴权媒体代理前不返回可公开访问的 URL。
    avatar_url = None
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
