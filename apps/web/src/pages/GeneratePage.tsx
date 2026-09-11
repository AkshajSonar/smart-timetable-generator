/**
 * GeneratePage — tenant ID + cohort picker → generate timetable → show grid.
 * Phase 1: no auth, user supplies tenantId manually.
 */

import { useState } from 'react';
import { api, type TimetableVersion, type LoadVerificationReport } from '../api/client';
import { TimetableGrid } from '../features/timetable-grid/TimetableGrid';
import { useTenant } from '../lib/TenantContext';

type Status = 'idle' | 'loading-cohorts' | 'ready' | 'generating' | 'done' | 'error';

export function GeneratePage() {
  const { tenantId, termId, tenantName, loading: tenantLoading, setLastVersionId } = useTenant();
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState('');
  const [timetable, setTimetable] = useState<TimetableVersion | null>(null);
  const [report, setReport] = useState<LoadVerificationReport | null>(null);
  const [violations, setViolations] = useState<{ h_code: string; message: string }[]>([]);
  const [generatedVersionId, setGeneratedVersionId] = useState<string>('');

  async function generate() {
    if (!tenantId || !termId) { setError('Tenant or Term not loaded yet — wait a moment.'); return; }
    setStatus('generating');
    setError('');
    setTimetable(null);
    setViolations([]);
    try {
      const genRes = await api.timetables.generate(tenantId, termId);
      setGeneratedVersionId(genRes.timetable_version_id);
      setLastVersionId(genRes.timetable_version_id); // share with other pages
      
      const tv = await api.timetables.get(tenantId, genRes.timetable_version_id);
      setTimetable(tv);
      setViolations(genRes.violations);
      
      try {
        const rep = await api.reports.getVerification(tenantId, genRes.timetable_version_id);
        setReport(rep);
      } catch (e) {
        console.warn("Could not load report", e);
      }
      
      setStatus('done');
    } catch (e: unknown) {
      setError((e as Error).message);
      setStatus('error');
    }
  }

  const busy = status === 'generating' || tenantLoading;

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg-deep)' }}>
      {/* Header */}
      <header className="border-b px-8 py-5 flex items-center gap-4" style={{ borderColor: 'var(--border)', background: 'var(--bg-card)' }}>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center text-lg" style={{ background: 'var(--accent)' }}>
          🗓
        </div>
        <div>
          <h1 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
            Smart Timetable Generator
          </h1>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            {tenantName ? `Tenant: ${tenantName}` : 'Loading tenant...'} · CP-SAT solver · H1–H11 guaranteed conflict-free
          </p>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-8 py-10 space-y-8">
        {/* Tenant info + generate */}
        <section className="rounded-2xl p-6 space-y-4" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
          <h2 className="text-sm font-semibold uppercase tracking-widest" style={{ color: 'var(--text-secondary)' }}>
            Generate Timetable
          </h2>
          <div className="flex gap-3 items-center">
            <div className="flex-1 text-sm font-mono rounded-lg px-4 py-2.5" style={{ background: 'var(--bg-panel)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}>
              {tenantLoading ? 'Resolving tenant…' : (tenantId || 'No tenant found')}
            </div>
            <button
              id="generate-btn"
              onClick={generate}
              disabled={busy || !tenantId || !termId}
              className="px-5 py-2.5 rounded-lg text-sm font-medium transition-all disabled:opacity-40 flex items-center gap-2"
              style={{ background: 'var(--accent)', color: '#fff' }}
            >
              {status === 'generating' && (
                <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              )}
              {status === 'generating' ? 'Solving…' : '⚡ Generate Timetable'}
            </button>
          </div>
        </section>

        {/* Error */}
        {status === 'error' && (
          <div className="rounded-xl px-5 py-4 text-sm" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#fca5a5' }}>
            ⚠ {error}
          </div>
        )}

        {/* Violations banner */}
        {violations.length > 0 && (
          <div className="rounded-xl px-5 py-4 text-sm space-y-1" style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', color: '#fcd34d' }}>
            <p className="font-semibold">⚠ Conflict checker found {violations.length} violation(s):</p>
            {violations.map((v, i) => (
              <p key={i} className="text-xs opacity-80">[{v.h_code}] {v.message}</p>
            ))}
          </div>
        )}

        {/* Verification Report */}
        {report && (
          <section className="rounded-2xl p-6 space-y-4" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
            <h2 className="text-sm font-semibold uppercase tracking-widest" style={{ color: 'var(--text-secondary)' }}>
              Load Verification Report
            </h2>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <h3 className="text-sm font-medium mb-2 text-emerald-400">Faculty Load</h3>
                <ul className="space-y-1">
                  {report.faculty_load.map(f => (
                    <li key={f.id} className="text-xs flex justify-between" style={{ color: 'var(--text-primary)' }}>
                      <span>{f.name}</span>
                      <span className={f.difference !== 0 ? 'text-red-400' : 'text-emerald-400'}>
                        {f.scheduled_hours}/{f.required_hours}h
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="text-sm font-medium mb-2 text-emerald-400">Cohort Load</h3>
                <ul className="space-y-1">
                  {report.cohort_load.map(c => (
                    <li key={c.id} className="text-xs flex justify-between" style={{ color: 'var(--text-primary)' }}>
                      <span>{c.name}</span>
                      <span className={c.difference !== 0 ? 'text-red-400' : 'text-emerald-400'}>
                        {c.scheduled_hours}/{c.required_hours}h
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        )}

        {/* Timetable */}
        {status === 'done' && timetable && (
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Generated Timetable
                </h2>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                  State: <span className="font-medium text-emerald-400">{timetable.state}</span>
                  {' · '}v{timetable.version_no}
                  {' · '}
                  {timetable.assignments.length} assignment{timetable.assignments.length !== 1 ? 's' : ''}
                  {violations.length === 0 && (
                    <span className="ml-2 text-emerald-400 font-medium">✓ No violations</span>
                  )}
                </p>
              </div>
            </div>
            {/* Version ID banner for easy copy-paste into other tabs */}
            <div className="px-4 py-3 rounded-xl text-xs font-mono flex items-center gap-2 select-all" style={{ background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.3)', color: '#a5b4fc' }}>
              <span className="font-sans font-semibold text-indigo-300">Version ID:</span>
              {generatedVersionId}
            </div>
            <TimetableGrid timetable={timetable} />
          </section>
        )}
      </main>
    </div>
  );
}
