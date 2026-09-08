/**
 * GeneratePage — tenant ID + cohort picker → generate timetable → show grid.
 * Phase 1: no auth, user supplies tenantId manually.
 */

import { useState } from 'react';
import { api, type TimetableVersion, type Cohort } from '../api/client';
import { TimetableGrid } from '../features/timetable-grid/TimetableGrid';

type Status = 'idle' | 'loading-cohorts' | 'ready' | 'generating' | 'done' | 'error';

export function GeneratePage() {
  const [tenantId, setTenantId] = useState('');
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [selectedCohort, setSelectedCohort] = useState('');
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState('');
  const [timetable, setTimetable] = useState<TimetableVersion | null>(null);
  const [violations, setViolations] = useState<{ h_code: string; message: string }[]>([]);

  async function loadCohorts() {
    if (!tenantId.trim()) return;
    setStatus('loading-cohorts');
    setError('');
    try {
      const res = await api.cohorts.list(tenantId.trim());
      setCohorts(res.items);
      setSelectedCohort(res.items[0]?.id ?? '');
      setStatus('ready');
    } catch (e: unknown) {
      setError((e as Error).message);
      setStatus('error');
    }
  }

  async function generate() {
    if (!selectedCohort) return;
    setStatus('generating');
    setError('');
    setTimetable(null);
    setViolations([]);
    try {
      const genRes = await api.timetables.generate(tenantId.trim(), selectedCohort);
      setViolations(genRes.violations);
      const tv = await api.timetables.get(tenantId.trim(), genRes.timetable_version_id);
      setTimetable(tv);
      setStatus('done');
    } catch (e: unknown) {
      setError((e as Error).message);
      setStatus('error');
    }
  }

  const busy = status === 'loading-cohorts' || status === 'generating';

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
            Phase 1 — CP-SAT solver · H1–H9 guaranteed conflict-free
          </p>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-8 py-10 space-y-8">
        {/* Step 1: Tenant */}
        <section className="rounded-2xl p-6 space-y-4" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
          <h2 className="text-sm font-semibold uppercase tracking-widest" style={{ color: 'var(--text-secondary)' }}>
            Step 1 — Tenant
          </h2>
          <div className="flex gap-3 items-end">
            <div className="flex-1 space-y-1.5">
              <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                Tenant ID (UUID)
              </label>
              <input
                id="tenant-id-input"
                type="text"
                placeholder="e.g. 3fa85f64-5717-4562-b3fc-2c963f66afa6"
                value={tenantId}
                onChange={e => setTenantId(e.target.value)}
                className="w-full rounded-lg px-4 py-2.5 text-sm font-mono outline-none transition-all"
                style={{
                  background: 'var(--bg-panel)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-primary)',
                }}
                onFocus={e => e.currentTarget.style.borderColor = 'var(--border-accent)'}
                onBlur={e => e.currentTarget.style.borderColor = 'var(--border)'}
              />
            </div>
            <button
              id="load-cohorts-btn"
              onClick={loadCohorts}
              disabled={busy || !tenantId.trim()}
              className="px-5 py-2.5 rounded-lg text-sm font-medium transition-all disabled:opacity-40"
              style={{ background: 'var(--accent)', color: '#fff' }}
            >
              {status === 'loading-cohorts' ? 'Loading…' : 'Load Cohorts'}
            </button>
          </div>
        </section>

        {/* Step 2: Cohort + Generate */}
        {cohorts.length > 0 && (
          <section className="rounded-2xl p-6 space-y-4" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
            <h2 className="text-sm font-semibold uppercase tracking-widest" style={{ color: 'var(--text-secondary)' }}>
              Step 2 — Generate
            </h2>
            <div className="flex gap-3 items-end">
              <div className="flex-1 space-y-1.5">
                <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                  Cohort
                </label>
                <select
                  id="cohort-select"
                  value={selectedCohort}
                  onChange={e => setSelectedCohort(e.target.value)}
                  className="w-full rounded-lg px-4 py-2.5 text-sm outline-none"
                  style={{
                    background: 'var(--bg-panel)',
                    border: '1px solid var(--border)',
                    color: 'var(--text-primary)',
                  }}
                >
                  {cohorts.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
              <button
                id="generate-btn"
                onClick={generate}
                disabled={busy || !selectedCohort}
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
        )}

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
            <TimetableGrid timetable={timetable} />
          </section>
        )}
      </main>
    </div>
  );
}
