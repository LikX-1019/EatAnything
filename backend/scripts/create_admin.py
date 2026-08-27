import argparse
import asyncio
import getpass
import sys
from pathlib import Path

from sqlalchemy import delete, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models import AdminUser, AdminUserSchool, School
from app.repositories.admins import get_admin_by_username


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="创建或更新 EatAnything 管理员账号")
    parser.add_argument("username", help="登录账号")
    parser.add_argument("--display-name", default=None, help="管理员显示名称")
    parser.add_argument(
        "--role",
        choices=("platform_admin", "school_admin"),
        default=None,
        help="管理员角色；新账号默认 platform_admin，更新账号时默认保持原角色",
    )
    parser.add_argument(
        "--school-id",
        action="append",
        type=int,
        default=None,
        help="学校管理员可管理的学校 ID；绑定多所学校时重复传入该参数",
    )
    return parser.parse_args()


async def configure_admin(args: argparse.Namespace, password: str) -> tuple[str, str, list[int]]:
    username = args.username.strip()
    if not username:
        raise SystemExit("登录账号不能为空")
    if len(password) < 8:
        raise SystemExit("密码至少需要 8 个字符")

    requested_school_ids = sorted(set(args.school_id or []))
    async with SessionFactory() as session:
        admin = await get_admin_by_username(session, username)
        target_role = args.role or (admin.role if admin is not None else "platform_admin")

        if target_role == "platform_admin" and requested_school_ids:
            raise SystemExit("platform_admin 不能绑定学校，请移除 --school-id")
        if target_role == "school_admin" and admin is None and not requested_school_ids:
            raise SystemExit("新建 school_admin 时至少需要一个 --school-id")

        if requested_school_ids:
            found_school_ids = set(
                await session.scalars(select(School.id).where(School.id.in_(requested_school_ids)))
            )
            missing_school_ids = sorted(set(requested_school_ids) - found_school_ids)
            if missing_school_ids:
                missing = ", ".join(str(value) for value in missing_school_ids)
                raise SystemExit(f"学校不存在：{missing}")

        if admin is None:
            admin = AdminUser(
                username=username,
                password_hash=hash_password(password),
                display_name=(args.display_name or username).strip(),
                role=target_role,
                status="active",
            )
            session.add(admin)
            await session.flush()
        else:
            admin.password_hash = hash_password(password)
            admin.display_name = (args.display_name or admin.display_name).strip()
            admin.role = target_role
            admin.status = "active"

        if target_role == "platform_admin":
            await session.execute(
                delete(AdminUserSchool).where(AdminUserSchool.admin_user_id == admin.id)
            )
            effective_school_ids: list[int] = []
        elif requested_school_ids:
            await session.execute(
                delete(AdminUserSchool).where(AdminUserSchool.admin_user_id == admin.id)
            )
            session.add_all(
                AdminUserSchool(admin_user_id=admin.id, school_id=school_id)
                for school_id in requested_school_ids
            )
            effective_school_ids = requested_school_ids
        else:
            effective_school_ids = list(
                await session.scalars(
                    select(AdminUserSchool.school_id).where(
                        AdminUserSchool.admin_user_id == admin.id
                    )
                )
            )
            if not effective_school_ids:
                raise SystemExit("school_admin 至少需要绑定一所学校，请传入 --school-id")

        await session.commit()
    return username, target_role, effective_school_ids


async def main() -> None:
    args = parse_args()
    password = getpass.getpass("请输入管理员密码（至少 8 个字符）：")
    username, role, school_ids = await configure_admin(args, password)
    school_summary = ",".join(str(value) for value in school_ids) if school_ids else "全部学校"
    print(f"管理员配置完成：账号={username}，角色={role}，范围={school_summary}")


if __name__ == "__main__":
    asyncio.run(main())
