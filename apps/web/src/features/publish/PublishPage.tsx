import { useState } from 'react';
import { Send, Users, Mail, Bell, Calendar as CalendarIcon, CheckCircle2, Loader2 } from 'lucide-react';
import { useTenant } from '../../lib/TenantContext';
import { api } from '../../api/client';

export function PublishPage() {
  const { tenantId, termId, lastVersionId } = useTenant();
  const [published, setPublished] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePublish = async () => {
    if (!tenantId || !lastVersionId) {
      setError("No timetable draft found to publish.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await api.timetables.publish(tenantId, lastVersionId);
      setPublished(true);
    } catch (err: any) {
      setError(err.message || "Failed to publish timetable.");
    } finally {
      setLoading(false);
    }
  };
  
  if (published) {
    return (
      <div className="max-w-2xl mx-auto py-24 text-center">
        <div className="w-24 h-24 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6">
          <CheckCircle2 className="w-12 h-12" />
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-4">Successfully Published!</h1>
        <p className="text-slate-500 mb-8">
          The timetable for {termId} is now live. Notifications are being sent out to faculty and students.
        </p>
        <button 
          onClick={() => window.location.href = '/dashboard'}
          className="bg-slate-900 hover:bg-slate-800 text-white font-medium px-8 py-3 rounded-xl transition-colors shadow-sm"
        >
          Return to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Publish Timetable</h1>
        <p className="text-slate-500">Make the approved timetable live and notify stakeholders.</p>
      </header>

      <div className="flex flex-col lg:flex-row gap-8">
        <div className="flex-1 space-y-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
            <h2 className="text-lg font-bold text-slate-900 mb-4">Notification Scope</h2>
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 flex items-center gap-4">
                <div className="w-10 h-10 bg-indigo-100 text-indigo-600 rounded-lg flex items-center justify-center shrink-0">
                  <Users className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900">86 Faculty</h3>
                  <p className="text-xs text-slate-500">Will receive schedules</p>
                </div>
              </div>
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 flex items-center gap-4">
                <div className="w-10 h-10 bg-emerald-100 text-emerald-600 rounded-lg flex items-center justify-center shrink-0">
                  <Users className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900">1,240 Students</h3>
                  <p className="text-xs text-slate-500">Will receive schedules</p>
                </div>
              </div>
            </div>

            <h2 className="text-lg font-bold text-slate-900 mb-4">Channels</h2>
            <div className="space-y-3 mb-8">
              <label className="flex items-center justify-between p-4 border border-slate-200 rounded-xl cursor-pointer hover:bg-slate-50 transition-colors">
                <div className="flex items-center gap-3">
                  <Mail className="w-5 h-5 text-slate-400" />
                  <span className="font-medium text-slate-700">Send Email Notification</span>
                </div>
                <input type="checkbox" defaultChecked className="w-5 h-5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-600" />
              </label>
              
              <label className="flex items-center justify-between p-4 border border-slate-200 rounded-xl cursor-pointer hover:bg-slate-50 transition-colors">
                <div className="flex items-center gap-3">
                  <Bell className="w-5 h-5 text-slate-400" />
                  <span className="font-medium text-slate-700">Send Push Notification (Mobile App)</span>
                </div>
                <input type="checkbox" defaultChecked className="w-5 h-5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-600" />
              </label>

              <label className="flex items-center justify-between p-4 border border-slate-200 rounded-xl cursor-pointer hover:bg-slate-50 transition-colors">
                <div className="flex items-center gap-3">
                  <CalendarIcon className="w-5 h-5 text-slate-400" />
                  <span className="font-medium text-slate-700">Sync to Google / Outlook Calendar</span>
                </div>
                <input type="checkbox" defaultChecked className="w-5 h-5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-600" />
              </label>
            </div>

            {error && (
              <div className="mb-4 p-4 rounded-xl border border-rose-200 bg-rose-50 text-rose-700 text-sm">
                {error}
              </div>
            )}

            <button 
              onClick={handlePublish}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 rounded-xl transition-all shadow-lg shadow-indigo-500/20 disabled:opacity-70"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              {loading ? 'Publishing...' : 'Publish & Notify'}
            </button>
          </div>
        </div>

        <div className="w-full lg:w-[450px] shrink-0">
          <div className="bg-slate-100 rounded-2xl p-6 h-full flex flex-col border border-slate-200">
            <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4">Email Preview</h3>
            
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex-1">
              <div className="p-4 border-b border-slate-100 bg-slate-50/50">
                <div className="flex gap-2 mb-2 text-sm">
                  <span className="text-slate-500 w-12">From:</span>
                  <span className="font-medium text-slate-900">Schedulr System &lt;no-reply@schedulr.edu&gt;</span>
                </div>
                <div className="flex gap-2 mb-2 text-sm">
                  <span className="text-slate-500 w-12">To:</span>
                  <span className="font-medium text-slate-900">All Faculty & Students</span>
                </div>
                <div className="flex gap-2 text-sm">
                  <span className="text-slate-500 w-12">Subj:</span>
                  <span className="font-medium text-slate-900">Timetable Published: {termId}</span>
                </div>
              </div>
              
              <div className="p-6">
                <div className="w-12 h-12 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold text-xl mb-6">S</div>
                <h4 className="text-xl font-bold text-slate-900 mb-4">Your timetable is ready</h4>
                <p className="text-slate-600 mb-4 text-sm leading-relaxed">
                  Hello,<br/><br/>
                  The academic timetable for <strong>{termId}</strong> has been finalized and published. 
                  You can now log in to the portal or check your synchronized calendar app to view your updated schedule.
                </p>
                <div className="my-8">
                  <a href="#" className="inline-block bg-indigo-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium">
                    View My Schedule
                  </a>
                </div>
                <p className="text-slate-500 text-xs mt-8 pt-4 border-t border-slate-100">
                  This is an automated message. Please do not reply directly to this email.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
