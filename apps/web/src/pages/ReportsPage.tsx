import { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, Users, Building2, Download, Loader2 } from 'lucide-react';
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
            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 overflow-hidden">
              <h3 className="font-bold text-slate-900 mb-4">Room Utilization Detail</h3>
              <div className="overflow-y-auto max-h-[300px]">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-slate-500 sticky top-0">
                    <tr>
                      <th className="py-2 px-3 font-medium">Room</th>
                      <th className="py-2 px-3 font-medium">Capacity</th>
                      <th className="py-2 px-3 font-medium text-right">Utilization</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {roomUtil?.rooms?.map((r: any) => (
                      <tr key={r.room_id}>
                        <td className="py-3 px-3 font-medium text-slate-900">{r.room_name}</td>
                        <td className="py-3 px-3 text-slate-500">{r.capacity}</td>
                        <td className="py-3 px-3 text-right">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            r.utilization_percentage > 80 ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-700'
                          }`}>
                            {r.utilization_percentage}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 overflow-hidden">
              <h3 className="font-bold text-slate-900 mb-4">Faculty Verification</h3>
              <div className="overflow-y-auto max-h-[300px]">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-slate-500 sticky top-0">
                    <tr>
                      <th className="py-2 px-3 font-medium">Faculty</th>
                      <th className="py-2 px-3 font-medium text-right">Req.</th>
                      <th className="py-2 px-3 font-medium text-right">Sch.</th>
                      <th className="py-2 px-3 font-medium text-right">Diff.</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {verification?.faculty_load?.map((f: any) => (
                      <tr key={f.id}>
                        <td className="py-3 px-3 font-medium text-slate-900">{f.name}</td>
                        <td className="py-3 px-3 text-right text-slate-500">{f.required_hours}h</td>
                        <td className="py-3 px-3 text-right text-slate-500">{f.scheduled_hours}h</td>
                        <td className="py-3 px-3 text-right">
                          <span className={`px-2 py-1 rounded text-xs font-bold ${
                            f.difference === 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                          }`}>
                            {f.difference > 0 ? '+' : ''}{f.difference}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
