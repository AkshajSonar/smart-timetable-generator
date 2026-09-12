import { useState } from 'react';
import { Calendar, CheckCircle2, Clock, MapPin, Users, Loader2 } from 'lucide-react';
import { examClient, type ExamSessionResult } from '../../api/examClient';
import { useTenant } from '../../lib/TenantContext';

export function ExamsModulePage() {
  const { tenantId, termId } = useTenant();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<ExamSessionResult[] | null>(null);
  const [versionId, setVersionId] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!tenantId || !termId) {
      setError("Please select a tenant and term first.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await examClient.generateExams(tenantId, termId);
      setResults(res.sessions);
      setVersionId(res.version_id);
    } catch (err: any) {
      setError(err.message || "Failed to generate exam timetable.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Exam Timetable Generation</h1>
          <p className="text-slate-500">Generate mathematically guaranteed clash-free exam schedules.</p>
        </div>
        <button 
          onClick={handleGenerate}
          disabled={loading}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors shadow-sm disabled:opacity-70"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calendar className="w-4 h-4" />}
          {loading ? 'Generating...' : 'Generate Exam Timetable'}
        </button>
      </header>

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 px-4 py-3 rounded-xl text-sm">
          {error}
        </div>
      )}

      {versionId && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-4 py-3 rounded-xl text-sm flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
          Successfully generated exam timetable. Version ID: <strong>{versionId}</strong>
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        {!results ? (
          <div className="p-12 text-center flex flex-col items-center justify-center">
            <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-4">
              <Calendar className="w-8 h-8 text-slate-300" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-1">No active exam timetable</h3>
            <p className="text-slate-500 max-w-sm">Click "Generate Exam Timetable" to assign exam slots, rooms, and invigilators based on course requirements.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 font-medium">Session ID</th>
                  <th className="px-6 py-3 font-medium">Course</th>
                  <th className="px-6 py-3 font-medium">Cohort</th>
                  <th className="px-6 py-3 font-medium">Room</th>
                  <th className="px-6 py-3 font-medium">Invigilator</th>
                  <th className="px-6 py-3 font-medium">Slot Index</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {results.map((r, i) => (
                  <tr key={i} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 font-mono text-xs text-slate-500">{r.id.substring(0, 8)}</td>
                    <td className="px-6 py-4 font-medium text-slate-900">{r.course_id.substring(0, 8)}</td>
                    <td className="px-6 py-4 text-slate-600 flex items-center gap-2">
                      <Users className="w-4 h-4 text-slate-400" />
                      {r.cohort_id.substring(0, 8)}
                    </td>
                    <td className="px-6 py-4 text-slate-600">
                      <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-slate-400" />
                        {r.room_id.substring(0, 8)}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-slate-600">
                      {r.invigilator_staff_profile_id ? (
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center font-bold text-[10px]">
                            IN
                          </div>
                          {r.invigilator_staff_profile_id.substring(0, 8)}
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">None</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 text-xs font-medium">
                        <Clock className="w-3.5 h-3.5" />
                        Slot {r.slot_start}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
