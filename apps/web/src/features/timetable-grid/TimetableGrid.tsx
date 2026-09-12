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

const COURSE_COLORS = [
  'from-indigo-50 to-indigo-100 border-indigo-200 text-indigo-900',
  'from-violet-50 to-violet-100 border-violet-200 text-violet-900',
  'from-sky-50 to-sky-100 border-sky-200 text-sky-900',
  'from-emerald-50 to-emerald-100 border-emerald-200 text-emerald-900',
  'from-amber-50 to-amber-100 border-amber-200 text-amber-900',
  'from-rose-50 to-rose-100 border-rose-200 text-rose-900',
  'from-cyan-50 to-cyan-100 border-cyan-200 text-cyan-900',
  'from-fuchsia-50 to-fuchsia-100 border-fuchsia-200 text-fuchsia-900',
];

interface Props {
  timetable: TimetableVersion;
}

export function TimetableGrid({ timetable }: Props) {
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

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200">
      <table className="w-full border-collapse min-w-[700px]">
        <thead>
          <tr>
            <th className="py-3 px-4 text-left text-xs font-semibold uppercase tracking-widest text-slate-500 bg-slate-50 border-b border-slate-200 w-24">
              Period
            </th>
            {DAYS.map(day => (
              <th
                key={day}
                className="py-3 px-4 text-center text-xs font-semibold uppercase tracking-widest text-slate-500 bg-slate-50 border-b border-slate-200"
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
              <td className="py-2 px-4 text-xs font-medium text-slate-500 border-b border-slate-100 bg-white whitespace-nowrap">
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
                      className="py-2 px-2 border-b border-r border-slate-100 last:border-r-0 group-hover:bg-slate-50 transition-colors"
                    />
                  );
                }

                return (
                  <td
                    key={dayIdx}
                    className="py-2 px-2 border-b border-r border-slate-100 last:border-r-0 align-top"
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
                              {a.course_name || a.course_id.slice(0, 8)}
                            </div>
                            <div className="mt-0.5 opacity-75 truncate">
                              {a.staff_name || 'Faculty'}
                            </div>
                            <div className="mt-0.5 opacity-60 text-[10px] truncate flex justify-between">
                              <span>🚪 {a.room_name || 'Room'}</span>
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
