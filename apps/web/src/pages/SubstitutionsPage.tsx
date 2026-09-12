import { useState, useEffect } from 'react';
import { RefreshCw, Search, CheckCircle2, Loader2, UserCheck, AlertCircle, Calendar, Plus, X } from 'lucide-react';
import { useTenant } from '../lib/TenantContext';
import { api, type StaffProfile, type TimetableVersion } from '../api/client';

export function SubstitutionsPage() {
  const { tenantId, lastVersionId } = useTenant();
  const [activeTab, setActiveTab] = useState('All Requests');
  const [substitutions, setSubstitutions] = useState<any[]>([]);
  const [staffList, setStaffList] = useState<StaffProfile[]>([]);
  const [timetable, setTimetable] = useState<TimetableVersion | null>(null);
  const [loading, setLoading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Absence Form State
  const [selectedStaffId, setSelectedStaffId] = useState('');
  const [absenceDate, setAbsenceDate] = useState(new Date().toISOString().split('T')[0]);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState('');
  const [candidates, setCandidates] = useState<{ staff_profile_id: string; current_load: number }[]>([]);
  const [substitutionId, setSubstitutionId] = useState<string | null>(null);
  const [selectedSubstituteId, setSelectedSubstituteId] = useState('');
  const [step, setStep] = useState<1 | 2>(1); // 1: Select Absence/Class, 2: Choose Substitute
  const [formError, setFormError] = useState<string | null>(null);
  const [formLoading, setFormLoading] = useState(false);

  const loadData = async () => {
    if (!tenantId) return;
    setLoading(true);
    try {
      const res = await api.substitutions.list(tenantId);
      setSubstitutions(res.items || []);

      const staffRes = await api.staff.list(tenantId);
      setStaffList(staffRes.items || []);

      if (lastVersionId) {
        const ttRes = await api.timetables.get(tenantId, lastVersionId);
        setTimetable(ttRes);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [tenantId, lastVersionId]);

  const handleFindSubstitutes = async () => {
    if (!tenantId || !selectedStaffId || !selectedAssignmentId) {
      setFormError("Please select both a faculty member and an assignment slot.");
      return;
    }
    setFormError(null);
    setFormLoading(true);

    try {
      const res = await api.substitutions.suggest(tenantId, {
        absent_staff_profile_id: selectedStaffId,
        assignment_id: selectedAssignmentId,
        date: absenceDate,
        version_no: timetable?.version_no ?? 1,
      });

      setSubstitutionId(res.substitution_id);
      setCandidates(res.candidates || []);
      setStep(2);
    } catch (err: any) {
      setFormError(err.message || "Failed to find substitutes for this assignment");
    } finally {
      setFormLoading(false);
    }
  };

  const handleConfirmSubstitution = async () => {
    if (!tenantId || !substitutionId || !selectedSubstituteId) {
      setFormError("Please select a candidate substitute.");
      return;
    }
    setFormError(null);
    setFormLoading(true);

    try {
      await api.substitutions.confirm(tenantId, substitutionId, {
        substitute_staff_profile_id: selectedSubstituteId,
        version_no: timetable?.version_no ?? 1,
      });

      setIsModalOpen(false);
      setStep(1);
      setSelectedStaffId('');
      setSelectedAssignmentId('');
      setSelectedSubstituteId('');
      setCandidates([]);
      setSubstitutionId(null);
      await loadData();
    } catch (err: any) {
      setFormError(err.message || "Failed to confirm substitution");
    } finally {
      setFormLoading(false);
    }
  };

  // Filter staff assignments for selected staff
  const staffAssignments = timetable?.assignments.filter(
    a => a.staff_profile_id === selectedStaffId
  ) || [];

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Substitutions (FR-10.1, FR-10.2)</h1>
          <p className="text-slate-500">Declare faculty absences and match least-loaded eligible substitutes.</p>
        </div>
        <button 
          onClick={() => { setIsModalOpen(true); setStep(1); setFormError(null); }}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          Declare Absence / New Cover Request
        </button>
      </header>

      {/* Main Substitutions List Card */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between gap-4 bg-slate-50/50">
          <div className="relative w-72 shrink-0">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search substitution logs..." 
              className="w-full bg-white border border-slate-200 rounded-lg pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all placeholder:text-slate-400"
            />
          </div>
          <div className="flex gap-2 p-1 bg-slate-100 rounded-lg">
            {['All Requests', 'Confirmed', 'Suggested'].map(tab => (
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
            <div className="p-12 text-center flex flex-col items-center justify-center">
              <UserCheck className="w-12 h-12 text-slate-300 mb-3" />
              <h3 className="text-base font-bold text-slate-700">No active substitution requests</h3>
              <p className="text-slate-500 text-sm max-w-sm mt-1">Click "Declare Absence" above to log a faculty absence and auto-assign cover staff.</p>
            </div>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 font-medium">Date</th>
                  <th className="px-6 py-3 font-medium">Original Faculty ID</th>
                  <th className="px-6 py-3 font-medium">Substitute Faculty ID</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {substitutions
                  .filter(req => {
                    if (activeTab === 'Confirmed') return req.status === 'confirmed';
                    if (activeTab === 'Suggested') return req.status === 'suggested';
                    return true;
                  })
                  .map(req => (
                    <tr key={req.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="px-6 py-4 text-slate-900 font-medium">
                        {req.date}
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-slate-600">
                        {req.original_staff_profile_id}
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-slate-600">
                        {req.substitute_staff_profile_id ? (
                          <span className="font-semibold text-indigo-600">{req.substitute_staff_profile_id}</span>
                        ) : (
                          <span className="text-slate-400 italic">Pending Selection</span>
                        )}
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

      {/* Modal: Declare Absence & Find Substitutes */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4 animate-in fade-in">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">
                  {step === 1 ? 'Declare Faculty Absence' : 'Select Substitute Faculty'}
                </h3>
                <p className="text-slate-500 text-xs mt-0.5">
                  {step === 1 ? 'Select absent staff and the affected timetable slot' : 'Ranked least-loaded-first per §31 tie-break rule'}
                </p>
              </div>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="bg-rose-50 border border-rose-200 text-rose-700 p-3 rounded-xl text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            {step === 1 ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                    Absent Faculty Member
                  </label>
                  <select
                    value={selectedStaffId}
                    onChange={(e) => {
                      setSelectedStaffId(e.target.value);
                      setSelectedAssignmentId('');
                    }}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm font-medium focus:ring-2 focus:ring-indigo-500/20"
                  >
                    <option value="">-- Select Faculty --</option>
                    {staffList.map(s => (
                      <option key={s.id} value={s.id}>
                        Staff Profile ({s.id.slice(0, 8)}) - {s.employment_type}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                    Absence Date
                  </label>
                  <input
                    type="date"
                    value={absenceDate}
                    onChange={(e) => setAbsenceDate(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm font-medium focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                    Assignment Slot to Cover
                  </label>
                  {selectedStaffId && staffAssignments.length === 0 ? (
                    <div className="text-xs text-amber-600 bg-amber-50 p-3 rounded-xl border border-amber-200">
                      No assignments found for this staff member in active timetable.
                    </div>
                  ) : (
                    <select
                      value={selectedAssignmentId}
                      onChange={(e) => setSelectedAssignmentId(e.target.value)}
                      disabled={!selectedStaffId}
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm font-medium focus:ring-2 focus:ring-indigo-500/20 disabled:opacity-50"
                    >
                      <option value="">-- Select Class Assignment --</option>
                      {staffAssignments.map(a => (
                        <option key={a.id} value={a.id}>
                          Slot {a.slot_start} | Course {a.course_id.slice(0, 6)} | Cohort {a.cohort_id.slice(0, 6)}
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                  <button
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleFindSubstitutes}
                    disabled={formLoading || !selectedAssignmentId}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-5 py-2 rounded-xl text-sm font-medium shadow-sm"
                  >
                    {formLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                    Find Substitutes
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="text-xs text-slate-500">
                  Select an available candidate substitute from the list below:
                </div>

                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {candidates.map((c, idx) => (
                    <label
                      key={c.staff_profile_id}
                      className={`flex items-center justify-between p-3 rounded-xl border transition-all cursor-pointer ${
                        selectedSubstituteId === c.staff_profile_id
                          ? 'border-indigo-600 bg-indigo-50/60 ring-2 ring-indigo-500/20'
                          : 'border-slate-200 bg-white hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <input
                          type="radio"
                          name="substitute"
                          value={c.staff_profile_id}
                          checked={selectedSubstituteId === c.staff_profile_id}
                          onChange={(e) => setSelectedSubstituteId(e.target.value)}
                          className="text-indigo-600 focus:ring-indigo-500"
                        />
                        <div>
                          <div className="font-mono text-xs font-bold text-slate-900">
                            Staff {c.staff_profile_id.slice(0, 8)}
                          </div>
                          <div className="text-[11px] text-slate-500">
                            Rank #{idx + 1} • Workload Load: {c.current_load} classes
                          </div>
                        </div>
                      </div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md">
                        Eligible
                      </span>
                    </label>
                  ))}
                </div>

                <div className="flex justify-between gap-3 pt-4 border-t border-slate-100">
                  <button
                    onClick={() => setStep(1)}
                    className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800"
                  >
                    Back
                  </button>
                  <button
                    onClick={handleConfirmSubstitution}
                    disabled={formLoading || !selectedSubstituteId}
                    className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white px-5 py-2 rounded-xl text-sm font-medium shadow-sm"
                  >
                    {formLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                    Confirm Substitution
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
