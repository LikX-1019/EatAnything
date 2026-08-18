import argparse
import asyncio
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models import AdminUser
from app.repositories.admins import get_admin_by_username


async def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update a local Eat Anything administrator")
    parser.add_argument("username")
    parser.add_argument("--display-name", default=None)
    args = parser.parse_args()
    password = getpass.getpass("Password (min 8 characters): ")
    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters")
    async with SessionFactory() as session:
        admin = await get_admin_by_username(session, args.username)
        if admin is None:
            admin = AdminUser(username=args.username, password_hash=hash_password(password), display_name=args.display_name or args.username)
            session.add(admin)
        else:
            admin.password_hash = hash_password(password)
            admin.display_name = args.display_name or admin.display_name
            admin.status = "active"
        await session.commit()
    print(f"Administrator configured: {args.username}")


if __name__ == "__main__":
    asyncio.run(main())
