import asyncio
import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.future import select
from app.core.database import AsyncSessionLocal
from app.models.identity import Identity

async def main():
    parser = argparse.ArgumentParser(description="Bootstrap platform_super_admin role for a test identity")
    parser.add_argument("--email", default="superadmin@timetable.local", help="Email of the identity to elevate")
    args = parser.parse_args()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Identity).where(Identity.email == args.email))
        identity = result.scalar_one_or_none()

        if not identity:
            print(f"Error: Identity with email '{args.email}' not found.")
            print("Please log in via the frontend with this user first so auto-provisioning can create the Identity record.")
            sys.exit(1)

        if identity.platform_role == "platform_super_admin":
            print(f"Identity '{args.email}' already has platform_super_admin role.")
            sys.exit(0)

        identity.platform_role = "platform_super_admin"
        await session.commit()
        print(f"Success! Identity '{args.email}' has been granted platform_super_admin.")

if __name__ == "__main__":
    asyncio.run(main())
