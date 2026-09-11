import os
import glob
import re

files = [
    "departments.py", "courses.py", "rooms.py", 
    "period_templates.py", "cohorts.py", "staff_profiles.py", 
    "eligibility.py", "import_data.py"
]

for f in files:
    path = f"services/api/app/routers/{f}"
    with open(path, "r") as file:
        content = file.read()
    
    if "from app.rbac.dependencies import require_role" not in content:
        content = content.replace("router = APIRouter(", 
"""from app.rbac.dependencies import require_role
router = APIRouter(
    dependencies=[Depends(require_role(["institution_admin", "department_head"]))],
    """)
        with open(path, "w") as file:
            file.write(content)
        print(f"Updated {f}")

