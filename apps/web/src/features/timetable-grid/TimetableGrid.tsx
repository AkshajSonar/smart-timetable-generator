/**
 * TimetableGrid — read-only cohort-wise timetable view (§21.5).
 *
 * Renders assignments as coloured cells in a weekday × period grid.
 * Slot encoding: slot_start = weekday * periodsPerDay + period_index
 * (matches the slot_map built in the timetables router).
 */

import type { Assignment, TimetableVersion } from '../../api/client';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const PERIODS_PER_DAY = 6;

// Pastel palette per course (cycle by index)
const COURSE_COLORS = [
  'from-indigo-500/30 to-indigo-600/20 border-indigo-500/40 text-indigo-200',
  'from-violet-500/30 to-violet-600/20 border-violet-500/40 text-violet-200',
  'from-sky-500/30 to-sky-600/20 border-sky-500/40 text-sky-200',
  'from-emerald-500/30 to-emerald-600/20 border-emerald-500/40 text-emerald-200',
  'from-amber-500/30 to-amber-600/20 border-amber-500/40 text-amber-200',
  'from-rose-500/30 to-rose-600/20 border-rose-500/40 text-rose-200',
  'from-cyan-500/30 to-cyan-600/20 border-cyan-500/40 text-cyan-200',
  'from-fuchsia-500/30 to-fuchsia-600/20 border-fuchsia-500/40 text-fuchsia-200',
];

interface Props {
  timetable: TimetableVersion;
  /** Display name lookup maps — populated from master-data endpoints */
  courseNames?: Record<string, string>;
  facultyNames?: Record<string, string>;
  roomNames?: Record<string, string>;
}

export function TimetableGrid({ timetable, courseNames = {}, facultyNames = {}, roomNames = {} }: Props) {
  // Build a lookup: slot_start → array of assignments
  const bySlot = new Map<number, Assignment[]>();
  const courseColorIndex = new Map<string, number>();
  let colorIdx = 0;

  for (const a of timetable.assignments) {
    const list = bySlot.get(a.slot_start) || [];
    list.push(a);
    bySlot.set(a.slot_start, list);
    
    if (!courseColorIndex.has(a.course_id)) {
      courseColorIndex.set(a.course_id, colorIdx++ % COURSE_COLORS.length);
    }
  }

  const periods = Array.from({ length: PERIODS_PER_DAY }, (_, i) => i);

  const label = (id: string, map: Record<string, string>, fallback: string) =>
    map[id] ?? fallback;

  return (
    <div className="overflow-x-auto rounded-xl border border-white/8">
      <table className="w-full border-collapse min-w-[700px]">
        <thead>
          <tr>
            <th className="py-3 px-4 text-left text-xs font-semibold uppercase tracking-widest text-slate-500 bg-white/[0.03] border-b border-white/8 w-24">
              Period
            </th>
            {DAYS.map(day => (
              <th
                key={day}
                className="py-3 px-4 text-center text-xs font-semibold uppercase tracking-widest text-slate-400 bg-white/[0.03] border-b border-white/8"
              >
                {day}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {periods.map(period => (
            <tr key={period} className="group">
              {/* Period label */}
              <td className="py-2 px-4 text-xs font-medium text-slate-500 border-b border-white/[0.04] bg-white/[0.02] whitespace-nowrap">
                P{period + 1}
              </td>

              {/* Day cells */}
              {DAYS.map((_, dayIdx) => {
                const slot = dayIdx * PERIODS_PER_DAY + period;
                const assignments = bySlot.get(slot) || [];

                if (assignments.length === 0) {
                  return (
                    <td
                      key={dayIdx}
                      className="py-2 px-2 border-b border-r border-white/[0.04] last:border-r-0 group-hover:bg-white/[0.015] transition-colors"
                    />
                  );
                }

                return (
                  <td
                    key={dayIdx}
                    className="py-2 px-2 border-b border-r border-white/[0.04] last:border-r-0 align-top"
                  >
                    <div className="flex flex-col gap-1.5">
                      {assignments.map(a => {
                        const colorClass = COURSE_COLORS[courseColorIndex.get(a.course_id) ?? 0];
                        return (
                          <div
                            key={a.id}
                            className={`rounded-lg bg-gradient-to-br ${colorClass} border px-2.5 py-1.5 text-xs leading-tight`}
                          >
                            <div className="font-semibold truncate">
                              {label(a.course_id, courseNames, a.course_id.slice(0, 8))}
                            </div>
                            <div className="mt-0.5 opacity-75 truncate">
                              {label(a.staff_profile_id, facultyNames, 'Faculty')}
                            </div>
                            <div className="mt-0.5 opacity-60 text-[10px] truncate flex justify-between">
                              <span>🚪 {label(a.room_id, roomNames, 'Room')}</span>
                              {a.batch_id && <span>Batch</span>}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
