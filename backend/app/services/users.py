from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.minio import MinioStorage
from app.models import MediaObject
from app.repositories.users import user_stats


async def profile(session: AsyncSession, storage: MinioStorage, user) -> dict:
    # 头像通过带鉴权的 /api/v1/me/avatar/file 返回，小程序端用 request 域名即可加载；
    # 评价等他人可见列表仍使用占位，不暴露头像地址。
    avatar_url = None
    if user.avatar_media_id is not None:
        avatar = await session.get(MediaObject, user.avatar_media_id)
        if avatar is not None:
            avatar_url = "/api/v1/me/avatar/file"
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
        "gender": user.gender,
        "birthday": user.birthday.isoformat() if user.birthday is not None else None,
        "level": user.level,
        "stats": await user_stats(session, user.id),
        "created_at": user.created_at.isoformat(),
    }
