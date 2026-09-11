import asyncio
import time
import uuid
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.core.database import AsyncSessionLocal
from sqlalchemy import text
from app.services.generation import build_solver_input
from solver.model import solve
from solver.conflict_checker import check_all

async def test_generation():
    tenant_id_str = "782f5084-efbc-4aa5-a581-035b77d4de08"
    tenant_id = uuid.UUID(tenant_id_str)
    
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
            {"tenant_id": str(tenant_id)}
        )
        
        # Get term_id
        res = await session.execute(text("SELECT id FROM timetable_version WHERE tenant_id = :tid LIMIT 1").bindparams(tid=tenant_id))
        term_id = res.scalar()
        if not term_id:
            term_id = uuid.uuid4() # Fallback if no version exists
        
        print(f"Building solver input for tenant {tenant_id}, term {term_id}...")
        t0 = time.time()
        solver_input, _, _, _, _, _ = await build_solver_input(session, tenant_id, term_id=term_id)
        t1 = time.time()
        print(f"Input build took {t1 - t0:.2f} seconds")
        
    print(f"Running CP-SAT solver...")
    t2 = time.time()
    result = solve(solver_input)
    t3 = time.time()
    solve_time = t3 - t2
    print(f"Solve took {solve_time:.2f} seconds")
    
    if result is None:
        print("Result: INFEASIBLE")
    else:
        print("Result: FEASIBLE")
        print(f"Total assignments made: {len(result)}")
        
        print("Running independent conflict checker...")
        t4 = time.time()
        violations = check_all(result, solver_input)
        t5 = time.time()
        print(f"Check took {t5 - t4:.2f} seconds")
        if violations:
            print(f"WARNING: Found {len(violations)} violations!")
            for v in violations:
                print(f"  {v}")
        else:
            print("SUCCESS: 0 hard constraint violations (invariant #2 verified)")

if __name__ == "__main__":
    asyncio.run(test_generation())
