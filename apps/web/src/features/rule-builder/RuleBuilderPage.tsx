import { useState, useEffect } from 'react';
import { api, type Rule } from '../../api/client';
import { useTenant } from '../../lib/TenantContext';
import { Wand2, Check, ShieldAlert, FileText, Trash2, Edit2, Loader2 } from 'lucide-react';

interface ParsedRule {
  id: string;
  confirmation_text: string;
  parsed_fields: any;
}

export function RuleBuilderPage() {
  const { tenantId } = useTenant();
  const [nlInput, setNlInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [parsed, setParsed] = useState<ParsedRule | null>(null);
  
  const [rules, setRules] = useState<Rule[]>([]);
  const [loadingRules, setLoadingRules] = useState(true);

  const loadRules = async () => {
    if (!tenantId) return;
    try {
      const res = await api.rules.list(tenantId);
      // Only show confirmed rules in the list
      setRules(res.filter(r => r.status === 'confirmed'));
    } catch (err: any) {
      console.error('Failed to load rules:', err);
    } finally {
      setLoadingRules(false);
    }
  };

  useEffect(() => {
    loadRules();
  }, [tenantId]);

  const handleParse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nlInput.trim()) return;
    
    setLoading(true);
    setError(null);
    setSuccess(null);
    setParsed(null);
    
    try {
      const data = await api.rules.parse(tenantId, nlInput);
      if (data.parsed_fields && data.parsed_fields.rule_type === 'unsupported') {
        setError("I couldn't understand that rule. Please try phrasing it differently or use the manual builder.");
      } else {
        setParsed(data);
      }
    } catch (err: any) {
      setError(err.message || "Failed to parse rule");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!parsed) return;
    setLoading(true);
    try {
      await api.rules.confirm(tenantId, parsed.id, parsed.parsed_fields);
      setSuccess("Rule confirmed and saved.");
      setParsed(null);
      setNlInput('');
      await loadRules(); // Refresh the list
    } catch (err: any) {
      setError(err.message || "Failed to confirm rule");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (ruleId: string) => {
    if (!confirm('Are you sure you want to delete this rule?')) return;
    try {
      await api.rules.delete(tenantId, ruleId);
      await loadRules();
    } catch (err: any) {
      alert('Failed to delete rule: ' + err.message);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Constraint Rules</h1>
        <p className="text-slate-500">Define the logic that powers your timetable generation.</p>
      </header>

      {/* AI Rule Builder Area */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <div className="p-6 bg-indigo-50/50 border-b border-slate-200">
          <h2 className="text-lg font-bold text-slate-900 mb-1 flex items-center gap-2">
            <Wand2 className="w-5 h-5 text-indigo-600" />
            Add Natural Language Rule
          </h2>
          <p className="text-sm text-slate-500">Describe what you need, and our AI will translate it into system logic.</p>
        </div>
        
        <div className="p-6">
          <form onSubmit={handleParse} className="space-y-4">
            <textarea 
              value={nlInput}
              onChange={(e) => setNlInput(e.target.value)}
              placeholder="e.g., 'Prof. Smith shouldn't teach on Fridays' or 'Prefer morning classes for CS Core subjects'"
              className="w-full bg-slate-50 border border-slate-200 rounded-xl p-4 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all min-h-[120px] resize-none"
            />
            <div className="flex justify-end">
              <button 
                type="submit"
                disabled={loading || !nlInput.trim()}
                className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-300 disabled:cursor-not-allowed text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-colors shadow-sm"
              >
                {loading && !parsed ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                {loading && !parsed ? 'Analyzing...' : 'Analyze Rule'}
              </button>
            </div>
          </form>

          {error && (
            <div className="mt-4 p-4 rounded-xl border border-rose-200 bg-rose-50 text-rose-700 text-sm flex gap-3">
              <ShieldAlert className="w-5 h-5 shrink-0" />
              <p>{error}</p>
            </div>
          )}

          {success && (
            <div className="mt-4 p-4 rounded-xl border border-emerald-200 bg-emerald-50 text-emerald-700 text-sm flex gap-3">
              <Check className="w-5 h-5 shrink-0" />
              <p>{success}</p>
            </div>
          )}

          {/* AI Confirmation Card */}
          {parsed && (
            <div className="mt-6 border-2 border-indigo-100 bg-indigo-50/30 rounded-2xl p-6">
              <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
                <FileText className="w-5 h-5 text-indigo-600" />
                Review Interpretation
              </h3>
              
              <div className="bg-white rounded-xl p-4 border border-indigo-100 shadow-sm mb-6">
                <p className="text-slate-700 font-medium">{parsed.confirmation_text}</p>
                <div className="mt-4 pt-4 border-t border-slate-100 grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-slate-400 block text-xs uppercase font-bold tracking-wider mb-1">Rule Type</span>
                    <span className="font-mono bg-slate-50 px-2 py-1 rounded text-indigo-700">{parsed.parsed_fields?.rule_type}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-xs uppercase font-bold tracking-wider mb-1">Target</span>
                    <span className="font-medium text-slate-700">{parsed.parsed_fields?.target_id || 'System-wide'}</span>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3">
                <button 
                  onClick={() => setParsed(null)}
                  className="px-5 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
                >
                  Discard
                </button>
                <button 
                  onClick={handleConfirm}
                  disabled={loading}
                  className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl transition-colors shadow-sm"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  Confirm & Save
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Active Rules List */}
      <div>
        <h2 className="text-lg font-bold text-slate-900 mb-4">Active Rules</h2>
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto min-h-[200px]">
            {loadingRules ? (
              <div className="flex items-center justify-center h-full pt-12">
                <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
              </div>
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-3 font-medium w-24">Type</th>
                    <th className="px-6 py-3 font-medium">Description</th>
                    <th className="px-6 py-3 font-medium w-24">Weight</th>
                    <th className="px-6 py-3 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {rules.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-6 py-8 text-center text-slate-500">
                        No active rules found. Use the builder above to create one.
                      </td>
                    </tr>
                  ) : (
                    rules.map((r) => {
                      const isHard = r.weight === null;
                      return (
                        <tr key={r.id} className="hover:bg-slate-50/50 transition-colors">
                          <td className="px-6 py-4">
                            <span className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium uppercase tracking-wider ${
                              isHard ? 'bg-rose-50 text-rose-700' : 'bg-emerald-50 text-emerald-700'
                            }`}>
                              {isHard ? 'HARD' : 'SOFT'}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-slate-700 font-medium">
                            {r.raw_input_text || `Structured Rule: ${r.rule_type}`}
                            <div className="text-xs font-mono text-slate-400 mt-1">{r.rule_type}</div>
                          </td>
                          <td className="px-6 py-4 text-slate-500 font-mono">{r.weight || 'N/A'}</td>
                          <td className="px-6 py-4 flex items-center justify-end gap-2 text-slate-400">
                            <button className="p-1 hover:text-indigo-600 transition-colors rounded">
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button 
                              onClick={() => handleDelete(r.id)}
                              className="p-1 hover:text-rose-600 transition-colors rounded"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
