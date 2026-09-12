import { useState, useEffect } from 'react';
import { RefreshCw, Search, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { useTenant } from '../lib/TenantContext';
import { api } from '../api/client';

export function SubstitutionsPage() {
  const { tenantId } = useTenant();
  const [activeTab, setActiveTab] = useState('All Requests');
  const [substitutions, setSubstitutions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    async function load() {
      if (!tenantId) return;
      setLoading(true);
      try {
        const res = await api.substitutions.list(tenantId);
        setSubstitutions(res.items || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [tenantId]);

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Substitutions</h1>
          <p className="text-slate-500">Manage temporary faculty replacements and cover requests.</p>
        </div>
        <button className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors shadow-sm">
          <RefreshCw className="w-4 h-4" />
          New Request
        </button>
      </header>

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between gap-4 bg-slate-50/50">
          <div className="relative w-72 shrink-0">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search requests..." 
              className="w-full bg-white border border-slate-200 rounded-lg pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all placeholder:text-slate-400"
            />
          </div>
          <div className="flex gap-2 p-1 bg-slate-100 rounded-lg">
            {['All Requests', 'Pending Approval', 'Open Requests', 'History'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  activeTab === tab ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto min-h-[300px] relative">
          {loading ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            </div>
          ) : substitutions.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              No substitution requests found.
            </div>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 font-medium">Date</th>
                  <th className="px-6 py-3 font-medium">Original Faculty</th>
                  <th className="px-6 py-3 font-medium">Substitute</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {substitutions.map(req => (
                  <tr key={req.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-6 py-4 text-slate-900 font-medium">
                      {req.date}
                    </td>
                    <td className="px-6 py-4">
                      {req.original_staff_profile_id}
                    </td>
                    <td className="px-6 py-4">
                      {req.substitute_staff_profile_id || 'Pending'}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                        req.status === 'confirmed' ? 'bg-emerald-100 text-emerald-700' :
                        req.status === 'suggested' ? 'bg-amber-100 text-amber-700' :
                        'bg-slate-100 text-slate-700'
                      }`}>
                        {req.status === 'confirmed' && <CheckCircle2 className="w-3.5 h-3.5" />}
                        {req.status === 'suggested' && <Search className="w-3.5 h-3.5" />}
                        {req.status.charAt(0).toUpperCase() + req.status.slice(1)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
