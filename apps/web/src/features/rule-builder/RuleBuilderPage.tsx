import { useState } from 'react';
import { api } from '../../api/client';
import { useTenant } from '../../lib/TenantContext';

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
  
  // For edit mode or fallback structured form
  const [editMode, setEditMode] = useState(false);
  const [structuredData, setStructuredData] = useState<any>({
    rule_type: '',
    scope: 'tenant',
    target_id: '',
    threshold: 0,
    unit: '',
    polarity: 'positive',
    weight: 0
  });

  const handleParse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nlInput.trim()) return;
    
    setLoading(true);
    setError(null);
    setSuccess(null);
    setParsed(null);
    setEditMode(false);
    
    try {
      const data = await api.rules.parse(tenantId, nlInput);
      if (data.parsed_fields && data.parsed_fields.rule_type === 'unsupported') {
        // Fallback to structured form
        setEditMode(true);
        setStructuredData(data.parsed_fields);
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
      await api.rules.confirm(tenantId, parsed.id);
      setSuccess("Rule confirmed and applied successfully!");
      setParsed(null);
      setNlInput('');
    } catch (err: any) {
      setError(err.message || "Failed to confirm rule");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateStructured = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = { ...structuredData };
      if (!payload.target_id) delete payload.target_id;
      if (payload.threshold === '') delete payload.threshold;
      if (payload.weight === '') delete payload.weight;
      
      await api.rules.create(tenantId, payload);
      setSuccess("Structured rule created successfully!");
      setEditMode(false);
      setParsed(null);
      setNlInput('');
    } catch (err: any) {
      setError(err.message || "Failed to create rule");
    } finally {
      setLoading(false);
    }
  };

  const startEdit = () => {
    if (parsed) {
      setStructuredData(parsed.parsed_fields);
    }
    setEditMode(true);
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold tracking-tight text-white">Rule Builder</h1>
        <p className="text-slate-400">Describe scheduling rules in plain English. The system will parse them and confirm the interpretation before applying.</p>
      </header>

      <form onSubmit={handleParse} className="flex gap-4 items-end">
        <div className="flex-1">
          <label className="block text-sm font-medium text-slate-300 mb-2">Rule Description</label>
          <input
            type="text"
            className="w-full px-4 py-3 bg-slate-900 border border-white/10 rounded-xl text-white focus:outline-none focus:border-indigo-500"
            placeholder="e.g. 'Professor Smith cannot teach on Fridays'"
            value={nlInput}
            onChange={(e) => setNlInput(e.target.value)}
          />
        </div>
        <button
          type="submit"
          disabled={!nlInput.trim() || loading}
          className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-xl transition-colors disabled:opacity-50 h-12"
        >
          {loading && !parsed && !editMode ? 'Parsing...' : 'Parse Rule'}
        </button>
      </form>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
        </div>
      )}

      {success && (
        <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400">
          {success}
        </div>
      )}

      {parsed && !editMode && (
        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 space-y-6">
          <div>
            <h3 className="text-lg font-medium text-white mb-2">Confirmation</h3>
            <p className="text-slate-300 text-lg leading-relaxed bg-slate-900 p-4 rounded-xl border border-white/5">
              {parsed.confirmation_text}
            </p>
          </div>
          <div className="flex gap-4">
            <button
              onClick={handleConfirm}
              disabled={loading}
              className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
            >
              Confirm & Apply
            </button>
            <button
              onClick={startEdit}
              disabled={loading}
              className="px-6 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-lg transition-colors disabled:opacity-50"
            >
              Edit Structured Fields
            </button>
          </div>
        </div>
      )}

      {editMode && (
        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 space-y-4">
          <h3 className="text-lg font-medium text-white">Structured Rule Fallback</h3>
          <p className="text-sm text-slate-400 mb-4">
            The parser returned 'unsupported' or you chose to manually edit. Fill in the structured fields directly.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm text-slate-300">Rule Type</label>
              <input type="text" className="px-3 py-2 bg-slate-900 border border-white/10 rounded-lg text-white" value={structuredData.rule_type || ''} onChange={e => setStructuredData({...structuredData, rule_type: e.target.value})} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm text-slate-300">Scope</label>
              <input type="text" className="px-3 py-2 bg-slate-900 border border-white/10 rounded-lg text-white" value={structuredData.scope || ''} onChange={e => setStructuredData({...structuredData, scope: e.target.value})} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm text-slate-300">Target ID (UUID)</label>
              <input type="text" className="px-3 py-2 bg-slate-900 border border-white/10 rounded-lg text-white" value={structuredData.target_id || ''} onChange={e => setStructuredData({...structuredData, target_id: e.target.value})} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm text-slate-300">Threshold</label>
              <input type="number" className="px-3 py-2 bg-slate-900 border border-white/10 rounded-lg text-white" value={structuredData.threshold || ''} onChange={e => setStructuredData({...structuredData, threshold: e.target.value})} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm text-slate-300">Unit</label>
              <input type="text" className="px-3 py-2 bg-slate-900 border border-white/10 rounded-lg text-white" value={structuredData.unit || ''} onChange={e => setStructuredData({...structuredData, unit: e.target.value})} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm text-slate-300">Polarity</label>
              <select className="px-3 py-2 bg-slate-900 border border-white/10 rounded-lg text-white" value={structuredData.polarity || 'positive'} onChange={e => setStructuredData({...structuredData, polarity: e.target.value})}>
                <option value="positive">Positive</option>
                <option value="negative">Negative</option>
              </select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm text-slate-300">Weight</label>
              <input type="number" className="px-3 py-2 bg-slate-900 border border-white/10 rounded-lg text-white" value={structuredData.weight || ''} onChange={e => setStructuredData({...structuredData, weight: e.target.value})} />
            </div>
          </div>
          <div className="pt-4 flex gap-4">
            <button
              onClick={handleCreateStructured}
              disabled={loading}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
            >
              Create Rule
            </button>
            <button
              onClick={() => { setEditMode(false); setParsed(null); }}
              className="px-6 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-lg transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
