import { useEffect, useState } from 'react';
import { Search, Plus, Edit2, Trash2, Loader2 } from 'lucide-react';
import { api, type StaffProfile } from '../api/client';
import { useTenant } from '../lib/TenantContext';

function generateAvatar(id: string) {
  return id.charAt(0).toUpperCase();
}

function generateName(id: string) {
  // Deterministic mock name based on UUID for demo purposes since full_name is in Identity table
  const names = ['Sarah Johnson', 'Amit Sharma', 'Priya Mehta', 'Rohit Verma', 'Neha Singh', 'Karan Patel', 'Alice Admin', 'David DeptHead'];
  const num = parseInt(id.replace(/-/g, '').substring(0, 8), 16);
  return 'Dr. ' + names[num % names.length];
}

export function FacultyPage() {
  const { tenantId } = useTenant();
  const [faculty, setFaculty] = useState<StaffProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    async function loadData() {
      if (!tenantId) return;
      try {
        const res = await api.staff.list(tenantId);
        setFaculty(res.items);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [tenantId]);

  const filteredFaculty = faculty.filter(f => {
    const name = generateName(f.identity_id);
    if (search && !name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Faculty</h1>
          <p className="text-slate-500">Manage faculty profiles, availability and workload.</p>
        </div>
        <button className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors shadow-sm">
          <Plus className="w-4 h-4" />
          Add Faculty
        </button>
      </header>

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/50">
          <div className="relative w-72">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search faculty..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-white border border-slate-200 rounded-lg pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all placeholder:text-slate-400"
            />
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
                  <th className="px-6 py-3 font-medium">Employment</th>
                  <th className="px-6 py-3 font-medium">Max Daily Hrs</th>
                  <th className="px-6 py-3 font-medium">Max Weekly Hrs</th>
                  <th className="px-6 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredFaculty.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-slate-500">
                      No faculty profiles found.
                    </td>
                  </tr>
                ) : (
                  filteredFaculty.map((f) => {
                    const name = generateName(f.identity_id);
                    return (
                      <tr key={f.id} className="hover:bg-slate-50/50 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm shrink-0">
                              {generateAvatar(name.replace('Dr. ', '').replace('Prof. ', ''))}
                            </div>
                            <span className="font-medium text-slate-900">{name}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className={`px-2 py-1 rounded-md text-xs font-medium ${
                            f.employment_type === 'full_time' ? 'bg-indigo-50 text-indigo-700' : 'bg-amber-50 text-amber-700'
                          }`}>
                            {f.employment_type === 'full_time' ? 'Full-time' : 'Part-time'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-slate-600">{f.workload_cap_day} hrs</td>
                        <td className="px-6 py-4 text-slate-600">{f.workload_cap_week} hrs</td>
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
                    );
                  })
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
