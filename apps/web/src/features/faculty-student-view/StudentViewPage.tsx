import { useState, useEffect } from 'react';
import { api, type TimetableVersion, type Student } from '../../api/client';
import { TimetableGrid } from '../timetable-grid/TimetableGrid';
import { useTenant } from '../../lib/TenantContext';
import { Loader2 } from 'lucide-react';

export function StudentViewPage() {
  const { tenantId, lastVersionId } = useTenant();
  const [timetable, setTimetable] = useState<TimetableVersion | null>(null);
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState<string>('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function load() {
      if (!tenantId || !lastVersionId) return;
      setLoading(true);
      try {
        const [fullTimetable, studentsRes] = await Promise.all([
          api.timetables.get(tenantId, lastVersionId),
          api.students.list(tenantId)
        ]);
        setTimetable(fullTimetable);
        setStudents(studentsRes.items);
        if (studentsRes.items.length > 0) {
          setSelectedStudentId(studentsRes.items[0].id);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [tenantId, lastVersionId]);

  const selectedStudent = students.find(s => s.id === selectedStudentId);
  const filteredTimetable = timetable && selectedStudent ? {
    ...timetable,
    assignments: timetable.assignments.filter(a => a.cohort_id === selectedStudent.cohort_id)
  } : null;

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">My Timetable (Student)</h1>
          <p className="text-slate-500">View your personalized class schedule.</p>
        </div>
        <div className="flex items-center gap-4">
          <select 
            value={selectedStudentId}
            onChange={(e) => setSelectedStudentId(e.target.value)}
            className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 shadow-sm"
          >
            {students.map(s => (
              <option key={s.id} value={s.id}>{s.name} ({s.cohort_name})</option>
            ))}
          </select>
          <div className="flex gap-2 p-1 bg-slate-100 rounded-lg">
            <button className="px-3 py-1.5 text-sm font-medium rounded-md bg-white text-indigo-600 shadow-sm transition-colors">Grid View</button>
            <button className="px-3 py-1.5 text-sm font-medium rounded-md text-slate-600 hover:text-slate-900 transition-colors">List View</button>
          </div>
        </div>
      </header>

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden min-h-[400px] relative">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
          </div>
        ) : filteredTimetable ? (
          <div className="p-6">
            <TimetableGrid 
              timetable={filteredTimetable}
            />
          </div>
        ) : (
          <div className="p-12 text-center text-slate-500">No timetable published yet.</div>
        )}
      </div>
    </div>
  );
}
