from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.models.staff_profile import StaffProfile
from app.models.course import Course
from app.models.cohort import Cohort
from app.models.identity import Identity
from app.rule_parser.llm_client import ParsedRule


async def validate_and_resolve_rule(
    db: AsyncSession, tenant_id: UUID, parsed_rule: ParsedRule
) -> ParsedRule:
    """Validate rule schema semantics and resolve target_id to a real UUID."""
    if parsed_rule.rule_type == "unsupported":
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "VALIDATION_ERROR", "message": "Unsupported rule type. Please use the structured form."}},
        )

    resolved_target_id = None
    
    if parsed_rule.scope != "tenant" and parsed_rule.target_id:
        target = parsed_rule.target_id
        
        # Try to resolve based on scope
        if parsed_rule.scope == "department":
            q = await db.execute(select(Department).where(Department.name.ilike(f"%{target}%")))
            dept = q.scalars().first()
            if not dept:
                raise HTTPException(status_code=422, detail={"error": {"code": "VALIDATION_ERROR", "message": f"Department '{target}' not found."}})
            resolved_target_id = str(dept.id)
            
        elif parsed_rule.scope == "faculty":
            # Faculty search by identity full_name
            q = await db.execute(
                select(StaffProfile)
                .join(Identity, StaffProfile.identity_id == Identity.id)
                .where(Identity.full_name.ilike(f"%{target}%"))
            )
            staff = q.scalars().first()
            if not staff:
                raise HTTPException(status_code=422, detail={"error": {"code": "VALIDATION_ERROR", "message": f"Faculty '{target}' not found."}})
            resolved_target_id = str(staff.id)
            
        elif parsed_rule.scope == "course":
            q = await db.execute(select(Course).where(Course.name.ilike(f"%{target}%")))
            course = q.scalars().first()
            if not course:
                raise HTTPException(status_code=422, detail={"error": {"code": "VALIDATION_ERROR", "message": f"Course '{target}' not found."}})
            resolved_target_id = str(course.id)
            
        elif parsed_rule.scope == "cohort":
            q = await db.execute(select(Cohort).where(Cohort.name.ilike(f"%{target}%")))
            cohort = q.scalars().first()
            if not cohort:
                raise HTTPException(status_code=422, detail={"error": {"code": "VALIDATION_ERROR", "message": f"Cohort '{target}' not found."}})
            resolved_target_id = str(cohort.id)
            
        parsed_rule.target_id = resolved_target_id

    return parsed_rule
