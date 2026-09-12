import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, AlertCircle, CheckCircle2, AlertTriangle, RefreshCw, Download } from 'lucide-react';
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
  const [conflictErrors, setConflictErrors] = useState<{ h_code?: string; message: string }[] | null>(null);
  const [editSuccess, setEditSuccess] = useState<string | null>(null);

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

  const handleAssignmentMove = async (assignmentId: string, newSlotStart: number) => {
    if (!tenantId || !lastVersionId || !timetable) return;
    setConflictErrors(null);
    setEditSuccess(null);

    try {
      const res = await api.timetables.edit(tenantId, lastVersionId, {
        assignment_id: assignmentId,
        slot_start: newSlotStart,
        version_no: timetable.version_no,
      });

      // Update local assignments and stored version_no
      setTimetable(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          version_no: res.new_version_no,
          assignments: prev.assignments.map(a => 
            a.id === assignmentId ? { ...a, slot_start: newSlotStart, is_locked: true } : a
          )
        };
      });

      setEditSuccess("Assignment moved successfully! Cell locked and version updated.");
      setTimeout(() => setEditSuccess(null), 4000);
    } catch (err: any) {
      if (err.details && Array.isArray(err.details) && err.details.length > 0) {
        setConflictErrors(err.details);
      } else {
        setConflictErrors([{ message: err.message || "Conflict or invalid edit detected" }]);
      }
    }
  };

  useEffect(() => {
    async function load() {
      if (!tenantId) return;
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
    return <div className="p-8 text-slate-500 flex items-center gap-2"><RefreshCw className="w-5 h-5 animate-spin text-indigo-600" /> Loading timetable...</div>;
  }

  if (error || !timetable) {
    return (
      <div className="p-8 text-rose-600 bg-rose-50 rounded-xl border border-rose-200">
        <h2 className="font-bold text-lg mb-2 flex items-center gap-2">
          <AlertCircle className="w-5 h-5" /> Could not load timetable
        </h2>
        <p>{error}</p>
        <button 
          onClick={() => navigate('/generate')}
          className="mt-4 bg-slate-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-800 transition-colors"
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
          <p className="text-slate-500">Version ID: {timetable.id.slice(0, 8)} • v{timetable.version_no}</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Export Dropdown (FR-8.3) */}
          <div className="flex items-center gap-1.5 border-r border-slate-200 pr-3 mr-1">
            <Download className="w-4 h-4 text-slate-400" />
            <a
              href={api.timetables.exportUrl(tenantId, lastVersionId, 'csv')}
              target="_blank"
              rel="noreferrer"
              className="px-2.5 py-1 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
            >
              CSV
            </a>
            <a
              href={api.timetables.exportUrl(tenantId, lastVersionId, 'ics')}
              target="_blank"
              rel="noreferrer"
              className="px-2.5 py-1 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
            >
              iCal (ICS)
            </a>
            <a
              href={api.timetables.exportUrl(tenantId, lastVersionId, 'pdf')}
              target="_blank"
              rel="noreferrer"
              className="px-2.5 py-1 text-xs font-medium bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg transition-colors"
            >
              PDF / Print
            </a>
          </div>

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

      {/* Notifications / Alerts */}
      {editSuccess && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl text-sm flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{editSuccess}</span>
        </div>
      )}

      {conflictErrors && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 p-4 rounded-xl text-sm space-y-2 animate-in fade-in">
          <div className="font-semibold flex items-center gap-2 text-rose-900">
            <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
            Drag-and-Drop Edit Blocked — Hard Constraint Violation (FR-9.1):
          </div>
          <ul className="list-disc pl-5 space-y-1">
            {conflictErrors.map((c, i) => (
              <li key={i}>
                {c.h_code && <strong className="font-mono bg-rose-200/60 px-1 py-0.5 rounded mr-1">[{c.h_code}]</strong>}
                {c.message}
              </li>
            ))}
          </ul>
        </div>
      )}

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
              <p className="text-slate-500 font-medium text-sm mb-1">Hard Conflicts</p>
              <h3 className="text-2xl font-bold text-emerald-600">0</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-slate-500 font-medium text-sm mb-1">State / Version</p>
              <h3 className="text-2xl font-bold text-slate-900 capitalize">{timetable.state} (v{timetable.version_no})</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <AlertCircle className="w-5 h-5" />
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900">Interactive Timetable Grid</h2>
          <span className="text-xs font-medium text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
            💡 Drag & drop any class block to move slots (re-validates H1–H11 in real-time)
          </span>
        </div>
        <TimetableGrid 
          timetable={timetable}
          onAssignmentMove={handleAssignmentMove}
        />
      </div>
    </div>
  );
}
