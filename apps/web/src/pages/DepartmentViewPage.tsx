import { useState, useEffect } from 'react';
import { api, type TimetableVersion, type Department, type Course } from '../api/client';
import { TimetableGrid } from '../features/timetable-grid/TimetableGrid';
import { useTenant } from '../lib/TenantContext';
import { Loader2, Building, BookOpen, Users, Clock } from 'lucide-react';

export function DepartmentViewPage() {
  const { tenantId, lastVersionId } = useTenant();
  const [timetable, setTimetable] = useState<TimetableVersion | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedDeptId, setSelectedDeptId] = useState<string>('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function load() {
      if (!tenantId) return;
      setLoading(true);
      try {
        const deptRes = await api.departments.list(tenantId);
        const deptList = deptRes.items || [];
        setDepartments(deptList);
        if (deptList.length > 0) {
          setSelectedDeptId(deptList[0].id);
        }

        const courseRes = await api.courses.list(tenantId);
        setCourses(courseRes.items || []);

        if (lastVersionId) {
          const fullTimetable = await api.timetables.get(tenantId, lastVersionId);
          setTimetable(fullTimetable);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [tenantId, lastVersionId]);

  // Find course IDs belonging to selected department
  const deptCourseIds = new Set(
    courses.filter(c => c.department_id === selectedDeptId).map(c => c.id)
  );

  // Filter timetable assignments by courses in selected department
  const filteredTimetable = timetable ? {
    ...timetable,
    assignments: timetable.assignments.filter(a => deptCourseIds.has(a.course_id))
  } : null;

  const activeDepartment = departments.find(d => d.id === selectedDeptId);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Department-wise Timetable (FR-8.1)</h1>
          <p className="text-slate-500">View schedule, course distribution, and resource allocations by department.</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Select Department:</label>
          <select 
            value={selectedDeptId}
            onChange={(e) => setSelectedDeptId(e.target.value)}
            className="bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 shadow-sm min-w-[200px]"
          >
            {departments.map(d => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>
      </header>

      {/* Department Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-slate-500 font-medium text-sm mb-1">Department</p>
              <h3 className="text-xl font-bold text-slate-900">{activeDepartment?.name || 'Selected Department'}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Building className="w-5 h-5" />
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-slate-500 font-medium text-sm mb-1">Department Courses</p>
              <h3 className="text-2xl font-bold text-slate-900">{deptCourseIds.size}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-violet-50 text-violet-600 flex items-center justify-center">
              <BookOpen className="w-5 h-5" />
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-slate-500 font-medium text-sm mb-1">Scheduled Department Classes</p>
              <h3 className="text-2xl font-bold text-slate-900">{filteredTimetable?.assignments.length || 0}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Clock className="w-5 h-5" />
            </div>
          </div>
        </div>
      </div>

      {/* Main Department Timetable Grid */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm min-h-[400px] relative">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
          </div>
        ) : filteredTimetable ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-900">Department Schedule Matrix</h2>
              <span className="text-xs text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
                Showing all classes for {activeDepartment?.name}
              </span>
            </div>
            <TimetableGrid 
              timetable={filteredTimetable}
            />
          </div>
        ) : (
          <div className="p-12 text-center text-slate-500">
            No published timetable or department assignments found.
          </div>
        )}
      </div>
    </div>
  );
}
