"""
RBAC Dependencies implementing AGENTS.md Section 11 Permission Matrix.

Action                                 | Allowed roles
---------------------------------------|-------------------------------------------
Tenant configuration, module toggles   | institution_admin
Master data CRUD / bulk import         | institution_admin, department_head
Rule authoring (structured or NL)      | institution_admin, department_head
Trigger generation                     | institution_admin, department_head
Review and approve                     | reviewer
Publish                                | institution_admin
Manual edit                            | institution_admin, department_head
View own schedule                      | faculty, student
View all schedules / reports           | institution_admin, department_head, reviewer
Substitution management                | institution_admin, department_head
Default unlisted endpoints             | institution_admin
"""

from uuid import UUID
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.auth import verify_jwt
from app.models.staff_profile import StaffProfile
from app.models.student_profile import StudentProfile
from app.models.identity import Identity

from app.core.tenant_context import set_tenant_context

async def _get_user_roles(
    tenantId: UUID, 
    identity_id: UUID = Depends(verify_jwt), 
    db: AsyncSession = Depends(set_tenant_context)
) -> set[str]:
    user_roles = set()
    
    # Check student
    student_result = await db.execute(
        select(StudentProfile.id).where(
            StudentProfile.identity_id == identity_id,
            StudentProfile.tenant_id == tenantId
        )
    )
    if student_result.scalar_one_or_none():
        user_roles.add("student")
        
    # Check staff roles
    staff_result = await db.execute(
        select(StaffProfile.roles).where(
            StaffProfile.identity_id == identity_id,
            StaffProfile.tenant_id == tenantId
        )
    )
    # Fetch all matching staff profiles and aggregate roles
    staff_roles_list = staff_result.scalars().all()
    for staff_roles in staff_roles_list:
        if staff_roles:
            user_roles.update(staff_roles)
        
    return user_roles

def require_role(allowed_roles: list[str]):
    """
    Dependency factory to enforce tenant-scoped RBAC.
    """
    async def role_checker(
        tenantId: UUID,
        user_roles: set[str] = Depends(_get_user_roles)
    ):
        # If intersection is empty, forbid
        if not set(allowed_roles).intersection(user_roles):
            raise HTTPException(
                status_code=403,
                detail={"error": {"code": "FORBIDDEN", "message": f"Requires one of roles: {allowed_roles}"}}
            )
        return user_roles
            
    return role_checker

async def require_platform_super_admin(
    identity_id: UUID = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db)
):
    """
    Validates that the current identity has platform_super_admin role.
    This is NOT tenant-scoped, and is exclusively for POST /tenants.
    """
    result = await db.execute(select(Identity.platform_role).where(Identity.id == identity_id))
    platform_role = result.scalar_one_or_none()
    
    if platform_role != "platform_super_admin":
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "FORBIDDEN", "message": "Requires platform_super_admin role"}}
        )
