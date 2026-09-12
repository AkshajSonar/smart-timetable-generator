import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot, CheckCircle2, Zap, Loader2 } from 'lucide-react';
import { useTenant } from '../lib/TenantContext';
import { api, type Department, type AcademicTerm } from '../api/client';

export function GeneratePage() {
  const navigate = useNavigate();
  const { tenantId, termId } = useTenant();
  const [goal, setGoal] = useState('balanced');
  
  const [terms, setTerms] = useState<AcademicTerm[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedTerm, setSelectedTerm] = useState('');
  const [selectedDepts, setSelectedDepts] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      if (!tenantId) return;
      try {
        const [termRes, deptRes] = await Promise.all([
          api.terms.list(tenantId),
          api.departments.list(tenantId).catch(() => ({ items: [] as Department[] }))
        ]);
        setTerms(termRes.items);
        setDepartments(deptRes.items);
        
        if (termRes.items.length > 0) {
          setSelectedTerm(termId || termRes.items[0].id);
        }
        setSelectedDepts(deptRes.items.map(d => d.id));
      } catch (err) {
        console.error('Failed to load generate page data', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [tenantId, termId]);

  const handleGenerate = () => {
    navigate(`/progress?term=${selectedTerm}`);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Generate Timetable</h1>
        <p className="text-slate-500">Let our scheduling brain create the perfect timetable for you.</p>
      </header>

      <div className="flex flex-col lg:flex-row gap-8">
        <div className="flex-1 bg-white border border-slate-200 rounded-2xl p-6 shadow-sm relative min-h-[400px]">
          {loading ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            </div>
          ) : (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Term</label>
                <select 
                  value={selectedTerm}
                  onChange={(e) => setSelectedTerm(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 text-slate-900 font-medium"
                >
                  {terms.map(t => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                  {terms.length === 0 && <option>No terms available</option>}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-3">Departments</label>
                <div className="space-y-3 max-h-60 overflow-y-auto">
                  {departments.length === 0 ? (
                    <p className="text-sm text-slate-500">No departments found.</p>
                  ) : (
                    departments.map(dept => {
                      const isSelected = selectedDepts.includes(dept.id);
                      return (
                        <label key={dept.id} className="flex items-center gap-3 cursor-pointer group" onClick={(e) => {
                          e.preventDefault();
                          if (isSelected) {
                            setSelectedDepts(prev => prev.filter(id => id !== dept.id));
                          } else {
                            setSelectedDepts(prev => [...prev, dept.id]);
                          }
                        }}>
                          <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${
                            isSelected
                              ? 'bg-indigo-600 border-indigo-600'
                              : 'border-slate-300 group-hover:border-indigo-400'
                          }`}>
                            {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-white" />}
                          </div>
                          <span className="text-sm font-medium text-slate-700">{dept.name}</span>
                        </label>
                      );
                    })
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-3">Optimization Goal</label>
                <div className="space-y-3">
                  <label className="flex items-start gap-3 cursor-pointer group" onClick={() => setGoal('balanced')}>
                    <div className={`mt-0.5 w-4 h-4 rounded-full border-2 flex items-center justify-center ${goal === 'balanced' ? 'border-indigo-600' : 'border-slate-300'}`}>
                      {goal === 'balanced' && <div className="w-2 h-2 rounded-full bg-indigo-600" />}
                    </div>
                    <div>
                      <p className={`text-sm font-medium ${goal === 'balanced' ? 'text-indigo-900' : 'text-slate-700'}`}>Balanced workload</p>
                      <p className="text-xs text-slate-500 mt-0.5">Prioritizes even distribution of classes across the week.</p>
                    </div>
                  </label>
                  <label className="flex items-start gap-3 cursor-pointer group" onClick={() => setGoal('compact')}>
                    <div className={`mt-0.5 w-4 h-4 rounded-full border-2 flex items-center justify-center ${goal === 'compact' ? 'border-indigo-600' : 'border-slate-300'}`}>
                      {goal === 'compact' && <div className="w-2 h-2 rounded-full bg-indigo-600" />}
                    </div>
                    <div>
                      <p className={`text-sm font-medium ${goal === 'compact' ? 'text-indigo-900' : 'text-slate-700'}`}>Compact schedule</p>
                      <p className="text-xs text-slate-500 mt-0.5">Minimizes gaps between classes for students and faculty.</p>
                    </div>
                  </label>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="w-full lg:w-80 space-y-6">
          <div className="bg-indigo-900 text-white p-6 rounded-2xl relative overflow-hidden shadow-sm">
            <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full blur-2xl -mr-16 -mt-16"></div>
            <div className="relative z-10">
              <div className="w-12 h-12 bg-white/10 rounded-xl flex items-center justify-center mb-6">
                <Bot className="w-6 h-6 text-indigo-300" />
              </div>
              <h3 className="font-bold text-lg mb-2">Ready to generate?</h3>
              <p className="text-indigo-200 text-sm leading-relaxed mb-6">
                Our CP-SAT solver will analyze all hard and soft constraints to produce the optimal conflict-free schedule.
              </p>
              <button 
                onClick={handleGenerate}
                disabled={loading || selectedDepts.length === 0}
                className="w-full flex items-center justify-center gap-2 bg-white hover:bg-indigo-50 text-indigo-900 font-bold py-3 rounded-xl transition-colors shadow-lg disabled:opacity-50"
              >
                <Zap className="w-4 h-4 text-yellow-500" />
                Start Generation
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
