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
    <div className="max-w-5xl mx-auto space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Publish Timetable</h1>
        <p className="text-slate-500">Make the approved timetable live and notify stakeholders.</p>
      </header>

      <div className="flex flex-col lg:flex-row gap-8">
        
        {/* Left: Rocket Illustration & CTA */}
        <div className="w-full lg:w-96 flex flex-col items-center justify-center bg-sky-50/50 rounded-2xl border border-sky-100 p-8 text-center relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent to-sky-100/50"></div>
          
          <div className="relative z-10 flex flex-col items-center">
            <img 
              src="/rocket.png" 
              alt="Rocket launching" 
              className="w-full max-w-[240px] drop-shadow-xl mb-8 animate-bounce-slow"
            />
            
            <h3 className="font-black text-2xl text-slate-900 mb-2">Ready to publish?</h3>
            <p className="text-slate-600 text-sm font-medium mb-8 max-w-[250px]">
              Send the finalized timetables to students and faculty.
            </p>
            
            <button 
              onClick={handlePublish}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-4 rounded-xl transition-all shadow-lg shadow-indigo-600/20 disabled:opacity-50 group hover:scale-[1.02]"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />}
              {loading ? 'Publishing...' : 'Publish & Notify'}
            </button>
            {error && (
              <div className="mt-4 p-3 rounded-xl border border-rose-200 bg-rose-50 text-rose-700 text-sm w-full">
                {error}
              </div>
            )}
          </div>
        </div>

        {/* Right: Configuration */}
        <div className="flex-1 space-y-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
            <h2 className="text-lg font-bold text-slate-900 mb-4">Notification Scope</h2>
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 flex items-center gap-4">
                <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-xl flex items-center justify-center shrink-0">
                  <Users className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900">86 Faculty</h3>
                  <p className="text-xs text-slate-500">Will receive schedules</p>
                </div>
              </div>
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 flex items-center gap-4">
                <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-xl flex items-center justify-center shrink-0">
                  <Users className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900">1,240 Students</h3>
                  <p className="text-xs text-slate-500">Will receive schedules</p>
                </div>
              </div>
            </div>

            <h2 className="text-lg font-bold text-slate-900 mb-4">Channels</h2>
            <div className="space-y-3">
              <label className="flex items-center justify-between p-4 border border-slate-200 rounded-xl cursor-pointer hover:bg-slate-50 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-white border border-slate-200 flex items-center justify-center shadow-sm">
                    <Mail className="w-5 h-5 text-slate-500" />
                  </div>
                  <span className="font-medium text-slate-700">Send Email Notification</span>
                </div>
                <input type="checkbox" defaultChecked className="w-5 h-5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-600" />
              </label>
              
              <label className="flex items-center justify-between p-4 border border-slate-200 rounded-xl cursor-pointer hover:bg-slate-50 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-white border border-slate-200 flex items-center justify-center shadow-sm">
                    <Bell className="w-5 h-5 text-slate-500" />
                  </div>
                  <span className="font-medium text-slate-700">Send Push Notification (Mobile App)</span>
                </div>
                <input type="checkbox" defaultChecked className="w-5 h-5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-600" />
              </label>

              <label className="flex items-center justify-between p-4 border border-slate-200 rounded-xl cursor-pointer hover:bg-slate-50 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-white border border-slate-200 flex items-center justify-center shadow-sm">
                    <CalendarIcon className="w-5 h-5 text-slate-500" />
                  </div>
                  <span className="font-medium text-slate-700">Sync to Google / Outlook Calendar</span>
                </div>
                <input type="checkbox" defaultChecked className="w-5 h-5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-600" />
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
