import { useState } from 'react';
import { examClient, type ExamSessionResult } from '../../api/examClient';

export function ExamViews() {
  const [tenantId, setTenantId] = useState('00000000-0000-0000-0000-000000000000');
  const [termId, setTermId] = useState('00000000-0000-0000-0000-000000000000');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<ExamSessionResult[] | null>(null);
  const [versionId, setVersionId] = useState<string | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setResults(null);
    setVersionId(null);

    try {
      // Use the actual generated IDs if needed, but for the demo we'll just try to fetch
      // Wait, we need actual tenantId from somewhere. Let's hardcode the ones from the DB if user provides them, or provide an input.
      const res = await examClient.generateExams(tenantId, termId);
      setResults(res.sessions);
      setVersionId(res.version_id);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-white/10 rounded-xl p-6 flex flex-col gap-6">
      <div>
        <h2 className="text-xl font-bold text-white mb-2">Exam Module</h2>
        <p className="text-slate-400">Generate deterministic room-split exam timetables.</p>
      </div>

      <div className="flex gap-4">
        <input 
          type="text" 
          value={tenantId}
          onChange={(e) => setTenantId(e.target.value)}
          placeholder="Tenant ID"
          className="bg-slate-950 border border-white/10 rounded-lg px-4 py-2 text-white w-80"
        />
        <input 
          type="text" 
          value={termId}
          onChange={(e) => setTermId(e.target.value)}
          placeholder="Term ID"
          className="bg-slate-950 border border-white/10 rounded-lg px-4 py-2 text-white w-80"
        />
      </div>

      <div>
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg font-medium transition-colors disabled:opacity-50"
        >
          {loading ? 'Generating...' : 'Generate Exam Timetable'}
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-lg">
          {error}
        </div>
      )}

      {versionId && (
        <div className="bg-green-500/10 border border-green-500/20 text-green-400 p-4 rounded-lg">
          Successfully generated Exam Timetable Version: {versionId}
        </div>
      )}

      {results && results.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-slate-300">
            <thead className="bg-slate-950/50">
              <tr>
                <th className="p-3 font-medium">Session ID</th>
                <th className="p-3 font-medium">Course</th>
                <th className="p-3 font-medium">Cohort</th>
                <th className="p-3 font-medium">Room</th>
                <th className="p-3 font-medium">Invigilator</th>
                <th className="p-3 font-medium">Slot Index</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {results.map((r, i) => (
                <tr key={i} className="hover:bg-white/5">
                  <td className="p-3 text-sm font-mono">{r.id.substring(0, 8)}</td>
                  <td className="p-3 text-sm">{r.course_id.substring(0, 8)}</td>
                  <td className="p-3 text-sm">{r.cohort_id.substring(0, 8)}</td>
                  <td className="p-3 text-sm">{r.room_id.substring(0, 8)}</td>
                  <td className="p-3 text-sm">{r.invigilator_staff_profile_id ? r.invigilator_staff_profile_id.substring(0, 8) : 'None'}</td>
                  <td className="p-3 text-sm">{r.slot_start}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
