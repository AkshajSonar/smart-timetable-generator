import asyncio
from uuid import UUID
from app.core.database import get_db
from app.routers.timetables import get_timetable_version
from sqlalchemy import text

async def main():
    tenantId = UUID("d1c8367d-84fe-44b5-ad32-658dfdb46804")
    versionId = UUID("d38c5364-4254-4c42-8250-0fb8877bf612")
    async for db in get_db():
        await db.execute(text(f"SET LOCAL app.tenant_id = '{tenantId}'"))
        try:
            res = await get_timetable_version(
                tenantId=tenantId,
                versionId=versionId,
                db=db,
                _role={"institution_admin"}
            )
            print("SUCCESS:", res)
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
