import asyncio
import sys
import uuid
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.core.database import AsyncSessionLocal
from sqlalchemy import text
from app.services.generation import build_solver_input
from solver.model import _solve_classes
import solver.model as solver_model

# Monkey-patch builder functions
original_builders = [
    solver_model.build_h1_no_faculty_double_booking,
    solver_model.build_h2_no_cohort_double_booking,
    solver_model.build_h3_no_room_double_booking,
    solver_model.build_h4_faculty_unavailable_blocks,
    solver_model.build_h6_hours_match_required,
    solver_model.build_h8_workload_cap,
    solver_model.build_h10_shared_lab_capacity,
    solver_model.build_h11_no_student_double_booking,
]

async def debug():
    tenant_id_str = "5d6ef971-8b9e-4069-894b-df735193a414"
    tenant_id = uuid.UUID(tenant_id_str)
    
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT set_config('app.tenant_id', :tid, false)").bindparams(tid=str(tenant_id)))
        res = await session.execute(text("SELECT id FROM timetable_version WHERE tenant_id = :tid LIMIT 1").bindparams(tid=tenant_id))
        term_id = res.scalar() or uuid.uuid4()
        inp, _, _, _, _, _ = await build_solver_input(session, tenant_id, term_id=term_id)

    print("Checking constraints one by one...")
    for builder in original_builders:
        # Disable this constraint
        setattr(solver_model, builder.__name__, lambda *args, **kwargs: None)
        
        res = _solve_classes(inp, 10)
        status = "FEASIBLE" if res is not None else "INFEASIBLE"
        print(f"Without {builder.__name__}: {status}")
        
        # Restore
        setattr(solver_model, builder.__name__, builder)

if __name__ == "__main__":
    asyncio.run(debug())
