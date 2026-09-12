import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, AlertCircle, CheckCircle2 } from 'lucide-react';
import { api, type TimetableVersion } from '../api/client';
import { useTenant } from '../lib/TenantContext';
import { TimetableGrid } from '../features/timetable-grid/TimetableGrid';

export function ReviewTimetablePage() {
  const navigate = useNavigate();
  const { tenantId, lastVersionId } = useTenant();
  const [timetable, setTimetable] = useState<TimetableVersion | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleApprove = async () => {
    if (!tenantId || !lastVersionId) return;
    setApproving(true);
    try {
      await api.timetables.approve(tenantId, lastVersionId, timetable?.version_no ?? 1);
      navigate('/publish');
    } catch (err: any) {
      alert(err.message || "Failed to approve timetable");
      setApproving(false);
    }
  };

  useEffect(() => {
    async function load() {
      if (!tenantId) return;
      // In a real app we'd get the ID from URL or context. Using lastVersionId here.
      if (!lastVersionId) {
        setError("No generated timetable found. Please generate one first.");
        setLoading(false);
        return;
      }
      
      try {
        const fullTimetable = await api.timetables.get(tenantId, lastVersionId);
        setTimetable(fullTimetable);
      } catch (err: unknown) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [tenantId, lastVersionId]);

  if (loading) {
    return <div className="p-8 text-slate-500">Loading timetable...</div>;
  }

  if (error || !timetable) {
    return (
      <div className="p-8 text-rose-600 bg-rose-50 rounded-xl">
        <h2 className="font-bold mb-2">Could not load timetable</h2>
        <p>{error}</p>
        <button 
          onClick={() => navigate('/generate')}
          className="mt-4 bg-slate-900 text-white px-4 py-2 rounded-lg text-sm"
        >
          Go to Generate
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Review Draft</h1>
          <p className="text-slate-500">Version: {timetable.id.split('-')[0]}</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => navigate('/generate')}
            className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
          >
            Discard & Regenerate
          </button>
          <button 
            onClick={handleApprove}
            disabled={approving}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-xl text-sm font-medium transition-colors shadow-sm disabled:opacity-70"
          >
            <CheckCircle2 className="w-4 h-4" />
            {approving ? 'Approving...' : 'Approve & Publish'}
          </button>
        </div>
      </header>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-slate-500 font-medium text-sm mb-1">Assignments</p>
              <h3 className="text-2xl font-bold text-slate-900">{timetable.assignments.length}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <BookOpen className="w-5 h-5" />
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-slate-500 font-medium text-sm mb-1">Conflicts</p>
              <h3 className="text-2xl font-bold text-slate-900">0</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-slate-500 font-medium text-sm mb-1">Status</p>
              <h3 className="text-2xl font-bold text-slate-900 capitalize">{timetable.state}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <AlertCircle className="w-5 h-5" />
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        {/* We reuse the existing TimetableGrid component here */}
        <TimetableGrid 
          timetable={timetable}
        />
      </div>
    </div>
  );
}
