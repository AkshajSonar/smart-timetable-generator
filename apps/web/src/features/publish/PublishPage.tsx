import { useState } from 'react';
import { api, type TimetableVersion } from '../../api/client';
import { TimetableGrid } from '../timetable-grid/TimetableGrid';

const TENANT_ID = '00000000-0000-0000-0000-000000000000'; // Replace with real context later

export function PublishPage() {
  const [versionId, setVersionId] = useState<string>('');
  const [version, setVersion] = useState<TimetableVersion | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const handleFetchTimetable = async () => {
    if (!versionId) return;
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const data = await api.timetables.get(TENANT_ID, versionId);
      setVersion(data);
    } catch (err: any) {
      setError(err.message || "Failed to load timetable version");
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!version) return;
    try {
      setLoading(true);
      setError(null);
      await api.timetables.approve(TENANT_ID, version.id, version.version_no);
      setSuccessMsg("Timetable approved successfully!");
      // Refresh to get new state and version_no
      await handleFetchTimetable();
    } catch (err: any) {
      setError(err.message || "Failed to approve timetable");
      setLoading(false);
    }
  };

  const handlePublish = async () => {
    if (!version) return;
    try {
      setLoading(true);
      setError(null);
      await api.timetables.publish(TENANT_ID, version.id, version.version_no);
      setSuccessMsg("Timetable published successfully!");
      // Refresh to get new state and version_no
      await handleFetchTimetable();
    } catch (err: any) {
      setError(err.message || "Failed to publish timetable");
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold tracking-tight text-white">Review & Publish Workflow</h1>
        <p className="text-slate-400">Review generated timetables, approve them, and publish to the institution.</p>
      </header>

      <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/10 flex flex-wrap gap-4 items-end">
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
          disabled={!versionId || loading}
        >
          {loading ? 'Loading...' : 'Load Version'}
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
        </div>
      )}
      
      {successMsg && (
        <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400">
          {successMsg}
        </div>
      )}

      {version && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-4 items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/10">
            <div className="flex gap-6">
              <div>
                <span className="text-slate-400 text-sm">State: </span>
                <span className="text-white font-medium capitalize">{version.state}</span>
              </div>
              <div>
                <span className="text-slate-400 text-sm">Version No: </span>
                <span className="text-white font-medium">{version.version_no}</span>
              </div>
              <div>
                <span className="text-slate-400 text-sm">Approved By: </span>
                <span className="text-white font-medium">{version.approved_by ? "Yes" : "Pending"}</span>
              </div>
            </div>
            <div className="flex gap-3">
              <button 
                className="px-4 py-2 bg-amber-600/20 hover:bg-amber-600/30 text-amber-500 font-medium rounded-lg border border-amber-600/50 transition-colors disabled:opacity-50"
                onClick={handleApprove}
                disabled={loading || version.state === 'published' || version.approved_by !== null}
              >
                Approve (Reviewer)
              </button>
              <button 
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
                onClick={handlePublish}
                disabled={loading || version.state === 'published' || version.approved_by === null}
              >
                Publish (Admin)
              </button>
            </div>
          </div>
          <TimetableGrid timetable={version} />
        </div>
      )}
    </div>
  );
}
