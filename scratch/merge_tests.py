import re

old_file = 'services/api/tests/test_auth_rbac.py'
new_file = 'services/api/tests/test_auth_rbac.py.new'

with open(old_file, 'r') as f:
    old_content = f.read()

with open(new_file, 'r') as f:
    new_content = f.read()

# Tests to remove from old_content
tests_to_remove = [
    'test_student_timetable_ownership',
    'test_platform_super_admin_no_blanket_access',
    'test_platform_super_admin',
    'test_roles_db_lookup_end_to_end',
    'test_timetables_view_rbac_403_faculty' # superseded by test_get_timetable_rbac_403_faculty
]

for test_name in tests_to_remove:
    # Regex to find @pytest.mark.asyncio\nasync def test_name(...): ... up to the next @pytest.mark.asyncio or end of file
    pattern = r'@pytest\.mark\.asyncio\nasync def ' + test_name + r'\(.*?\):.*?(?=@pytest\.mark\.asyncio\n|$)'
    old_content = re.sub(pattern, '', old_content, flags=re.DOTALL)

with open(old_file, 'w') as f:
    f.write(old_content)
    f.write('\n')
    f.write(new_content)
