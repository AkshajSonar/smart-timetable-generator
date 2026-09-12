import { useEffect, useState } from 'react';
import { Search, Plus, Edit2, Trash2, Loader2 } from 'lucide-react';
import { api, type Course, type Department } from '../api/client';
import { useTenant } from '../lib/TenantContext';

export function CoursesPage() {
  const { tenantId } = useTenant();
  const [activeTab, setActiveTab] = useState('All');
  
  const [courses, setCourses] = useState<Course[]>([]);
  const [departments, setDepartments] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    async function loadData() {
      if (!tenantId) return;
      try {
        const [courseRes, deptRes] = await Promise.all([
          api.courses.list(tenantId),
          api.departments.list(tenantId).catch(() => ({ items: [] as Department[] }))
        ]);
        
        const deptMap = deptRes.items.reduce((acc, d) => {
          acc[d.id] = d.name;
          return acc;
        }, {} as Record<string, string>);
        
        setDepartments(deptMap);
        setCourses(courseRes.items);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [tenantId]);

  const filteredCourses = courses.filter(c => {
    if (activeTab !== 'All' && c.type.toLowerCase() !== activeTab.toLowerCase()) return false;
    if (search && !c.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Courses</h1>
          <p className="text-slate-500">Manage all courses, subjects and their configurations.</p>
        </div>
        <button className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors shadow-sm">
          <Plus className="w-4 h-4" />
          Add Course
        </button>
      </header>

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between gap-4 bg-slate-50/50">
          <div className="relative w-72 shrink-0">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search courses..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-white border border-slate-200 rounded-lg pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all placeholder:text-slate-400"
            />
          </div>
          <div className="flex gap-2 p-1 bg-slate-100 rounded-lg">
            {['All', 'Core', 'Elective', 'Lab'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  activeTab === tab ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto min-h-[300px]">
          {loading ? (
            <div className="flex items-center justify-center h-full pt-12">
              <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
            </div>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 font-medium">Name</th>
                  <th className="px-6 py-3 font-medium">Department</th>
                  <th className="px-6 py-3 font-medium">Type</th>
                  <th className="px-6 py-3 font-medium">Credits</th>
                  <th className="px-6 py-3 font-medium">Hours/Week</th>
                  <th className="px-6 py-3 font-medium">Block Size</th>
                  <th className="px-6 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredCourses.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-slate-500">
                      No courses found.
                    </td>
                  </tr>
                ) : (
                  filteredCourses.map((course) => (
                    <tr key={course.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="px-6 py-4 font-medium text-slate-900">{course.name}</td>
                      <td className="px-6 py-4 text-slate-600">{departments[course.department_id] || 'Unknown'}</td>
                      <td className="px-6 py-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-bold tracking-wide ${
                          course.type === 'core' ? 'bg-indigo-100 text-indigo-700' :
                          course.type === 'elective' ? 'bg-emerald-100 text-emerald-700' :
                          'bg-amber-100 text-amber-700'
                        }`}>
                          {course.type.charAt(0).toUpperCase() + course.type.slice(1)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-600">{course.credit_value}</td>
                      <td className="px-6 py-4 text-slate-600">{course.hours_per_week}</td>
                      <td className="px-6 py-4 text-slate-600">{course.block_size}</td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors">
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
