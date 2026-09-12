import { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, Users, Building2, Download, Loader2 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';
import { useTenant } from '../lib/TenantContext';
import { api, type LoadVerificationReport } from '../api/client';

export function ReportsPage() {
  const { tenantId, lastVersionId } = useTenant();
  const [loading, setLoading] = useState(false);
  const [verification, setVerification] = useState<LoadVerificationReport | null>(null);
  const [roomUtil, setRoomUtil] = useState<any | null>(null);

  useEffect(() => {
    async function loadData() {
      if (!tenantId || !lastVersionId) return;
      setLoading(true);
      try {
        const [verifRes, roomRes] = await Promise.all([
          api.reports.getVerification(tenantId, lastVersionId).catch(() => null),
          api.reports.getRoomUtilization(tenantId, lastVersionId).catch(() => null)
        ]);
        setVerification(verifRes);
        setRoomUtil(roomRes);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [tenantId, lastVersionId]);

  // Aggregate stats
  let avgUtil = 0;
  if (roomUtil && roomUtil.rooms && roomUtil.rooms.length > 0) {
    const total = roomUtil.rooms.reduce((sum: number, r: any) => sum + r.utilization_percentage, 0);
    avgUtil = total / roomUtil.rooms.length;
  }

  let loadBalance = 0;
  if (verification && verification.faculty_load && verification.faculty_load.length > 0) {
    const perfectMatches = verification.faculty_load.filter((f: any) => f.difference === 0).length;
    loadBalance = (perfectMatches / verification.faculty_load.length) * 100;
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Reports & Analytics</h1>
          <p className="text-slate-500">Insights into your institution's scheduling efficiency.</p>
        </div>
        <button className="flex items-center gap-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 px-4 py-2 rounded-xl text-sm font-medium transition-colors shadow-sm">
          <Download className="w-4 h-4" />
          Export Data
        </button>
      </header>

      {loading ? (
        <div className="flex items-center justify-center min-h-[300px]">
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
        </div>
      ) : !verification && !roomUtil ? (
        <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center text-slate-500 shadow-sm">
          Generate a timetable to view reports.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
              <div className="flex items-start justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                  <Building2 className="w-5 h-5" />
                </div>
              </div>
              <p className="text-slate-500 font-medium text-sm mb-1">Avg Room Utilization</p>
              <h3 className="text-2xl font-bold text-slate-900">{avgUtil.toFixed(1)}%</h3>
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
              <div className="flex items-start justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                  <Users className="w-5 h-5" />
                </div>
              </div>
              <p className="text-slate-500 font-medium text-sm mb-1">Faculty Load Balance</p>
              <h3 className="text-2xl font-bold text-slate-900">{loadBalance.toFixed(1)}%</h3>
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm opacity-50 cursor-not-allowed">
              <div className="flex items-start justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
                  <TrendingUp className="w-5 h-5" />
                </div>
              </div>
              <p className="text-slate-500 font-medium text-sm mb-1">Avg Student Gaps/Week</p>
              <h3 className="text-2xl font-bold text-slate-900">-- hrs</h3>
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm opacity-50 cursor-not-allowed">
              <div className="flex items-start justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                  <BarChart3 className="w-5 h-5" />
                </div>
              </div>
              <p className="text-slate-500 font-medium text-sm mb-1">Substitutions Filled</p>
              <h3 className="text-2xl font-bold text-slate-900">-- %</h3>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6">
              <h3 className="font-bold text-slate-900 mb-6">Room Utilization</h3>
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={roomUtil?.rooms || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="room_name" tick={{fontSize: 12, fill: '#64748b'}} axisLine={false} tickLine={false} />
                    <YAxis tick={{fontSize: 12, fill: '#64748b'}} axisLine={false} tickLine={false} tickFormatter={(val) => `${val}%`} />
                    <RechartsTooltip 
                      cursor={{fill: '#f8fafc'}}
                      contentStyle={{borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'}}
                    />
                    <Bar dataKey="utilization_percentage" name="Utilization" fill="#6366f1" radius={[4, 4, 0, 0]} barSize={32} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6">
              <h3 className="font-bold text-slate-900 mb-6">Faculty Load Verification</h3>
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={verification?.faculty_load || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{fontSize: 12, fill: '#64748b'}} axisLine={false} tickLine={false} />
                    <YAxis tick={{fontSize: 12, fill: '#64748b'}} axisLine={false} tickLine={false} />
                    <RechartsTooltip 
                      cursor={{fill: '#f8fafc'}}
                      contentStyle={{borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'}}
                    />
                    <Bar dataKey="required_hours" name="Required Hrs" fill="#cbd5e1" radius={[4, 4, 0, 0]} barSize={24} />
                    <Bar dataKey="scheduled_hours" name="Scheduled Hrs" fill="#10b981" radius={[4, 4, 0, 0]} barSize={24} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
