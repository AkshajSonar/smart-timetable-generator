import { useState } from 'react';
import { Calendar, CheckCircle2, Clock, MapPin, Users, Loader2, Grid, UserCheck, LayoutGrid, ShieldCheck } from 'lucide-react';
import { examClient, type ExamSessionResult } from '../../api/examClient';
import { useTenant } from '../../lib/TenantContext';

export function ExamsModulePage() {
  const { tenantId, termId } = useTenant();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<ExamSessionResult[] | null>(null);
  const [versionId, setVersionId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'seating' | 'roster'>('overview');
  const [selectedSessionIndex, setSelectedSessionIndex] = useState<number>(0);

  const handleGenerate = async () => {
    if (!tenantId || !termId) {
      setError("Please select a tenant and term first.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await examClient.generateExams(tenantId, termId);
      setResults(res.sessions);
      setVersionId(res.version_id);
    } catch (err: any) {
      setError(err.message || "Failed to generate exam timetable.");
    } finally {
      setLoading(false);
    }
  };

  const selectedSession = results && results[selectedSessionIndex] ? results[selectedSessionIndex] : null;

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Exam Timetable & Operations (FR-7.5)</h1>
          <p className="text-slate-500">Generate clash-free exam schedules, seating charts, and invigilator rosters.</p>
        </div>
        <button 
          onClick={handleGenerate}
          disabled={loading}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors shadow-sm disabled:opacity-70"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calendar className="w-4 h-4" />}
          {loading ? 'Generating...' : 'Generate Exam Timetable'}
        </button>
      </header>

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 px-4 py-3 rounded-xl text-sm">
          {error}
        </div>
      )}

      {versionId && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-4 py-3 rounded-xl text-sm flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
          Successfully generated exam timetable. Version ID: <strong>{versionId}</strong>
        </div>
      )}

      {/* View Selector Tabs */}
      {results && (
        <div className="flex border-b border-slate-200 gap-2">
          {[
            { id: 'overview', label: 'Session Overview', icon: Grid },
            { id: 'seating', label: 'Seating Chart View (FR-7.5)', icon: LayoutGrid },
            { id: 'roster', label: 'Invigilator Roster View (FR-7.5)', icon: UserCheck },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-all ${
                activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-600 bg-white'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        {!results ? (
          <div className="p-12 text-center flex flex-col items-center justify-center">
            <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-4">
              <Calendar className="w-8 h-8 text-slate-300" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-1">No active exam timetable</h3>
            <p className="text-slate-500 max-w-sm">Click "Generate Exam Timetable" to assign exam slots, rooms, seating arrangements, and invigilators.</p>
          </div>
        ) : activeTab === 'overview' ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 font-medium">Session ID</th>
                  <th className="px-6 py-3 font-medium">Course ID</th>
                  <th className="px-6 py-3 font-medium">Cohort ID</th>
                  <th className="px-6 py-3 font-medium">Room</th>
                  <th className="px-6 py-3 font-medium">Invigilator</th>
                  <th className="px-6 py-3 font-medium">Slot</th>
                  <th className="px-6 py-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {results.map((r, i) => (
                  <tr key={i} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 font-mono text-xs text-slate-500">{r.id.substring(0, 8)}</td>
                    <td className="px-6 py-4 font-medium text-slate-900">{r.course_id.substring(0, 8)}</td>
                    <td className="px-6 py-4 text-slate-600 flex items-center gap-2">
                      <Users className="w-4 h-4 text-slate-400" />
                      {r.cohort_id.substring(0, 8)}
                    </td>
                    <td className="px-6 py-4 text-slate-600">
                      <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-slate-400" />
                        {r.room_id.substring(0, 8)}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-slate-600">
                      {r.invigilator_staff_profile_id ? (
                        <div className="flex items-center gap-2">
                          <img 
                            src={`https://ui-avatars.com/api/?name=${r.invigilator_staff_profile_id}&background=random&color=fff&rounded=true&bold=true`}
                            alt="Invigilator"
                            className="w-6 h-6 rounded-full shadow-sm shrink-0"
                          />
                          {r.invigilator_staff_profile_id.substring(0, 8)}
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">Unassigned</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 text-xs font-medium">
                        <Clock className="w-3.5 h-3.5" />
                        Slot {r.slot_start}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => {
                          setSelectedSessionIndex(i);
                          setActiveTab('seating');
                        }}
                        className="text-indigo-600 hover:text-indigo-800 text-xs font-medium"
                      >
                        Seating Chart →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : activeTab === 'seating' ? (
          <div className="p-6 space-y-6">
            <div className="flex items-center justify-between bg-slate-50 p-4 rounded-xl border border-slate-200">
              <div className="flex items-center gap-4">
                <label className="text-xs font-bold uppercase text-slate-500">Select Exam Session:</label>
                <select
                  value={selectedSessionIndex}
                  onChange={(e) => setSelectedSessionIndex(Number(e.target.value))}
                  className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm font-medium"
                >
                  {results.map((r, idx) => (
                    <option key={idx} value={idx}>
                      Session #{r.id.slice(0, 6)} - Course {r.course_id.slice(0, 6)} (Room {r.room_id.slice(0, 6)})
                    </option>
                  ))}
                </select>
              </div>

              {selectedSession && (
                <div className="flex items-center gap-4 text-xs text-slate-600">
                  <span>🏛️ Room: <strong>{selectedSession.room_id.slice(0, 8)}</strong></span>
                  <span>👨‍🏫 Invigilator: <strong>{selectedSession.invigilator_staff_profile_id ? selectedSession.invigilator_staff_profile_id.slice(0, 8) : 'TBA'}</strong></span>
                  <span>⏰ Slot: <strong>Slot {selectedSession.slot_start}</strong></span>
                </div>
              )}
            </div>

            {selectedSession && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-900 flex items-center gap-2">
                    <LayoutGrid className="w-5 h-5 text-indigo-600" />
                    Room Seating Allocation Layout
                  </h3>
                  <span className="text-xs text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
                    Capacity: 40 Seats • Spacing Rule: Single Desk Split
                  </span>
                </div>

                {/* Seating Grid Visualization */}
                <div className="grid grid-cols-5 md:grid-cols-8 gap-3 bg-slate-900 p-6 rounded-2xl shadow-inner">
                  {Array.from({ length: 40 }, (_, seatIdx) => {
                    const seatNum = seatIdx + 1;
                    const isOccupied = seatNum <= 24; // Mock student seating pattern per deterministic split
                    const studentCode = isOccupied ? `STU-${1000 + seatNum}` : null;

                    return (
                      <div
                        key={seatIdx}
                        className={`aspect-square rounded-xl flex flex-col items-center justify-center p-2 border transition-all ${
                          isOccupied
                            ? 'bg-indigo-950/80 border-indigo-500/50 text-indigo-200 shadow-sm'
                            : 'bg-slate-950/40 border-white/5 text-slate-600'
                        }`}
                      >
                        <span className="text-[10px] font-mono opacity-60">Seat {seatNum}</span>
                        {isOccupied ? (
                          <>
                            <span className="text-xs font-bold text-white mt-1">{studentCode}</span>
                            <span className="text-[9px] text-indigo-300 truncate max-w-full">
                              Cohort {selectedSession.cohort_id.slice(0, 4)}
                            </span>
                          </>
                        ) : (
                          <span className="text-[10px] italic mt-1">Empty</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-slate-900 text-lg flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-indigo-600" />
                  Invigilator Assignment Roster (FR-7.5)
                </h3>
                <p className="text-slate-500 text-xs mt-0.5">Staff workload limits and session supervisory schedules</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {results
                .filter(r => r.invigilator_staff_profile_id)
                .map((session, idx) => (
                  <div key={idx} className="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-3 shadow-sm">
                    <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                      <div className="flex items-center gap-2">
                        <img 
                          src={`https://ui-avatars.com/api/?name=${session.invigilator_staff_profile_id}&background=random&color=fff&rounded=true&bold=true`}
                          alt="Invigilator"
                          className="w-8 h-8 rounded-full shadow-sm shrink-0"
                        />
                        <div>
                          <div className="font-bold text-slate-900 text-sm">
                            Staff Profile: {session.invigilator_staff_profile_id?.slice(0, 8)}
                          </div>
                          <div className="text-xs text-slate-500">Exam Invigilator</div>
                        </div>
                      </div>
                      <span className="bg-emerald-100 text-emerald-800 text-xs font-semibold px-2.5 py-1 rounded-full">
                        Assigned
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                        <span className="text-slate-400 block mb-0.5">Exam Session</span>
                        <strong className="text-slate-800">{session.id.slice(0, 8)}</strong>
                      </div>
                      <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                        <span className="text-slate-400 block mb-0.5">Exam Room</span>
                        <strong className="text-slate-800">{session.room_id.slice(0, 8)}</strong>
                      </div>
                      <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                        <span className="text-slate-400 block mb-0.5">Target Course</span>
                        <strong className="text-slate-800">{session.course_id.slice(0, 8)}</strong>
                      </div>
                      <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                        <span className="text-slate-400 block mb-0.5">Time Slot</span>
                        <strong className="text-slate-800">Slot {session.slot_start}</strong>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
