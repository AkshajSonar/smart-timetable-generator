import { useEffect, useState } from 'react';
import { api, type Assignment, type TimetableVersion } from '../../api/client';
import { TimetableGrid } from '../timetable-grid/TimetableGrid';

const TENANT_ID = '00000000-0000-0000-0000-000000000000'; // Replace with real context later

export function FacultyViewPage() {
  const [staff, setStaff] = useState<any[]>([]);
  const [selectedStaffId, setSelectedStaffId] = useState<string>('');
  
  // Actually we need a versionId to get assignments.
  // In a real app we'd fetch the published version or select one.
  const [versionId, setVersionId] = useState<string>('');
  
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Basic fetch of staff
    api.staff.list(TENANT_ID)
      .then(res => setStaff(res.items))
      .catch(e => console.error("Failed to load staff profiles", e));
  }, []);

  const handleFetchTimetable = async () => {
    if (!selectedStaffId || !versionId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.staff.getTimetable(TENANT_ID, selectedStaffId);
      // Ensure we only show assignments for this version (or just use all if API filtered it)
      // The backend API might not filter by version if it's meant to show the active one, 
      // but if the endpoint is like GET /staff-profiles/{id}/timetable?versionId=..., we'd pass it.
      // Wait, let me check backend. The spec says GET /staff-profiles/{id}/timetable returns assignments for published version.
      // For now, just set them.
      
      // Let's filter by version ID on the client side just in case, though the backend might already do it or we might need to pass it.
      // Wait, client.ts getTimetable doesn't take versionId for staff. Let's just use it as is.
      setAssignments(data);
    } catch (err: any) {
      setError(err.message || "Failed to load staff timetable");
    } finally {
      setLoading(false);
    }
  };

  const mockTimetableVersion: TimetableVersion = {
    id: versionId || 'faculty-view',
    tenant_id: TENANT_ID,
    state: 'published',
    version_no: 1,
    approved_by: 'system',
    assignments,
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold tracking-tight text-white">Faculty Timetable View</h1>
        <p className="text-slate-400">View an individualized timetable for a specific faculty member.</p>
      </header>

      <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/10 flex flex-wrap gap-4 items-end">
        <div className="flex flex-col gap-1.5 flex-1 min-w-[200px]">
          <label className="text-sm font-medium text-slate-300">Select Faculty</label>
          <select 
            className="px-3 py-2 bg-slate-900 border border-white/10 rounded-lg text-white focus:outline-none focus:border-indigo-500"
            value={selectedStaffId}
            onChange={(e) => setSelectedStaffId(e.target.value)}
          >
            <option value="">-- Choose Faculty --</option>
            {staff.map(s => (
              <option key={s.id} value={s.id}>
                {s.id.slice(0, 8)} - {s.employment_type}
              </option>
            ))}
          </select>
        </div>
        
        <div className="flex flex-col gap-1.5 flex-1 min-w-[200px]">
          <label className="text-sm font-medium text-slate-300">Timetable Version ID (Optional)</label>
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
          disabled={!selectedStaffId || loading}
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
      
      {!loading && assignments.length === 0 && selectedStaffId && !error && (
        <div className="p-8 text-center text-slate-500 border border-white/5 rounded-xl border-dashed">
          No assignments found for this faculty member.
        </div>
      )}
    </div>
  );
}
