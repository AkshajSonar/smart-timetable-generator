import { useEffect, useState } from 'react';
import { api, type Student, type Assignment, type TimetableVersion } from '../../api/client';
import { TimetableGrid } from '../timetable-grid/TimetableGrid';

const TENANT_ID = '00000000-0000-0000-0000-000000000000'; // Replace with real context later

export function StudentViewPage() {
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState<string>('');
  
  // Actually we need a versionId to get assignments.
  // In a real app we'd fetch the published version or select one.
  const [versionId, setVersionId] = useState<string>('');
  
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // We should also fetch course names, etc if needed.
  
  useEffect(() => {
    // Basic fetch of students
    // NOTE: Replace TENANT_ID with the context value.
    api.students.list(TENANT_ID)
      .then(res => setStudents(res.items))
      .catch(e => console.error("Failed to load students", e));
  }, []);

  const handleFetchTimetable = async () => {
    if (!selectedStudentId || !versionId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.students.getTimetable(TENANT_ID, selectedStudentId, versionId);
      setAssignments(data);
    } catch (err: any) {
      setError(err.message || "Failed to load student timetable");
    } finally {
      setLoading(false);
    }
  };

  const mockTimetableVersion: TimetableVersion = {
    id: versionId,
    tenant_id: TENANT_ID,
    state: 'published',
    version_no: 1,
    approved_by: 'system',
    assignments,
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold tracking-tight text-white">Student Timetable View</h1>
        <p className="text-slate-400">View an individualized timetable for a specific student, integrating their core batches and enrolled electives.</p>
      </header>

      <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/10 flex flex-wrap gap-4 items-end">
        <div className="flex flex-col gap-1.5 flex-1 min-w-[200px]">
          <label className="text-sm font-medium text-slate-300">Select Student</label>
          <select 
            className="px-3 py-2 bg-slate-900 border border-white/10 rounded-lg text-white focus:outline-none focus:border-indigo-500"
            value={selectedStudentId}
            onChange={(e) => setSelectedStudentId(e.target.value)}
          >
            <option value="">-- Choose Student --</option>
            {students.map(s => (
              <option key={s.id} value={s.id}>
                {s.external_student_code} (ID: {s.id.slice(0, 8)})
              </option>
            ))}
          </select>
        </div>
        
        <div className="flex flex-col gap-1.5 flex-1 min-w-[200px]">
          <label className="text-sm font-medium text-slate-300">Timetable Version ID</label>
          <input 
            type="text"
            className="px-3 py-2 bg-slate-900 border border-white/10 rounded-lg text-white focus:outline-none focus:border-indigo-500"
            placeholder="e.g. 123e4567-e89b-..."
            value={versionId}
            onChange={(e) => setVersionId(e.target.value)}
          />
        </div>

        <button 
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
          onClick={handleFetchTimetable}
          disabled={!selectedStudentId || !versionId || loading}
        >
          {loading ? 'Loading...' : 'View Timetable'}
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
        </div>
      )}

      {assignments.length > 0 && (
        <TimetableGrid timetable={mockTimetableVersion} />
      )}
      
      {!loading && assignments.length === 0 && selectedStudentId && versionId && !error && (
        <div className="p-8 text-center text-slate-500 border border-white/5 rounded-xl border-dashed">
          No assignments found for this student in this timetable version.
        </div>
      )}
    </div>
  );
}
