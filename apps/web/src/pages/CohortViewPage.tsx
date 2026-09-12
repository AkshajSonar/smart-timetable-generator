import { useState, useEffect } from 'react';
import { api, type TimetableVersion, type Cohort } from '../api/client';
import { TimetableGrid } from '../features/timetable-grid/TimetableGrid';
import { useTenant } from '../lib/TenantContext';
import { Loader2 } from 'lucide-react';

export function CohortViewPage() {
  const { tenantId, lastVersionId } = useTenant();
  const [timetable, setTimetable] = useState<TimetableVersion | null>(null);
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [selectedCohortId, setSelectedCohortId] = useState<string>('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function load() {
      if (!tenantId || !lastVersionId) return;
      setLoading(true);
      try {
        const fullTimetable = await api.timetables.get(tenantId, lastVersionId);
        setTimetable(fullTimetable);
        // We do not have api.cohorts in client.ts right now.
        // We will mock them by extracting from timetable assignments for now.
        const cohortMap = new Map<string, string>();
        for (const a of fullTimetable.assignments) {
          cohortMap.set(a.cohort_id, `Cohort ${a.cohort_id.substring(0,6)}`);
        }
        const extracted = Array.from(cohortMap.entries()).map(([id, name]) => ({ id, name, type: 'fixed' }));
        setCohorts(extracted as any);
        if (extracted.length > 0) {
          setSelectedCohortId(extracted[0].id);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [tenantId, lastVersionId]);

  const filteredTimetable = timetable ? {
    ...timetable,
    assignments: timetable.assignments.filter(a => a.cohort_id === selectedCohortId)
  } : null;

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Cohort Timetable</h1>
          <p className="text-slate-500">View the unified schedule for a specific cohort.</p>
        </div>
        <div className="flex items-center gap-4">
          <select 
            value={selectedCohortId}
            onChange={(e) => setSelectedCohortId(e.target.value)}
            className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 shadow-sm"
          >
            {cohorts.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
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
