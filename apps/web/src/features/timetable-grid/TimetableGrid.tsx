/**
 * TimetableGrid — interactive drag-and-drop timetable view (§21.3, FR-9.1).
 *
 * Renders assignments as coloured cards in a weekday × period grid.
 * Supports drag-and-drop cell moves with live conflict checking.
 * Slot encoding: slot_start = weekday * periodsPerDay + period_index
 */

import { useState } from 'react';
import type { Assignment, TimetableVersion } from '../../api/client';
import { Lock, Move } from 'lucide-react';

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
  onAssignmentMove?: (assignmentId: string, newSlotStart: number) => Promise<void>;
  readOnly?: boolean;
}

export function TimetableGrid({ timetable, onAssignmentMove, readOnly = false }: Props) {
  const [draggedAssignmentId, setDraggedAssignmentId] = useState<string | null>(null);
  const [dragOverSlot, setDragOverSlot] = useState<number | null>(null);

  // Build a lookup: slot_start → array of assignments
  const bySlot = new Map<number, (Assignment & { is_locked?: boolean; course_name?: string; staff_name?: string; room_name?: string })[]>();
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

  const handleDragStart = (e: React.DragEvent, assignmentId: string, currentSlot: number) => {
    if (readOnly || !onAssignmentMove) return;
    setDraggedAssignmentId(assignmentId);
    e.dataTransfer.setData('text/plain', JSON.stringify({ assignmentId, currentSlot }));
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent, slot: number) => {
    if (readOnly || !onAssignmentMove) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (dragOverSlot !== slot) {
      setDragOverSlot(slot);
    }
  };

  const handleDragLeave = (e: React.DragEvent, slot: number) => {
    if (dragOverSlot === slot) {
      setDragOverSlot(null);
    }
  };

  const handleDrop = async (e: React.DragEvent, targetSlot: number) => {
    e.preventDefault();
    setDragOverSlot(null);
    if (readOnly || !onAssignmentMove) return;

    try {
      const dataText = e.dataTransfer.getData('text/plain');
      if (!dataText) return;
      const data = JSON.parse(dataText);
      if (data.currentSlot !== targetSlot) {
        await onAssignmentMove(data.assignmentId, targetSlot);
      }
    } catch (err) {
      console.error("Drop handling error:", err);
    } finally {
      setDraggedAssignmentId(null);
    }
  };

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 shadow-sm bg-white">
      <table className="w-full border-collapse min-w-[750px]">
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
              <td className="py-3 px-4 text-xs font-medium text-slate-500 border-b border-slate-100 bg-white whitespace-nowrap">
                P{period + 1}
              </td>

              {DAYS.map((_, dayIdx) => {
                const slot = dayIdx * PERIODS_PER_DAY + period;
                const assignments = bySlot.get(slot) || [];
                const isOver = dragOverSlot === slot;

                return (
                  <td
                    key={dayIdx}
                    onDragOver={(e) => handleDragOver(e, slot)}
                    onDragLeave={(e) => handleDragLeave(e, slot)}
                    onDrop={(e) => handleDrop(e, slot)}
                    className={`py-2 px-2 border-b border-r border-slate-100 last:border-r-0 align-top transition-colors min-h-[90px] h-[90px] w-1/5 ${
                      isOver ? 'bg-indigo-50/80 border-indigo-300 ring-2 ring-indigo-400 ring-inset' : 'group-hover:bg-slate-50/40'
                    }`}
                  >
                    <div className="flex flex-col gap-1.5 h-full min-h-[70px]">
                      {assignments.map(a => {
                        const colorClass = COURSE_COLORS[courseColorIndex.get(a.course_id) ?? 0];
                        const isDraggingThis = draggedAssignmentId === a.id;
                        const canDrag = !readOnly && Boolean(onAssignmentMove);

                        return (
                          <div
                            key={a.id}
                            draggable={canDrag}
                            onDragStart={(e) => handleDragStart(e, a.id, slot)}
                            className={`group/card relative rounded-lg bg-gradient-to-br ${colorClass} border px-2.5 py-1.5 text-xs leading-tight transition-all duration-150 shadow-sm ${
                              canDrag ? 'cursor-grab active:cursor-grabbing hover:scale-[1.02] hover:shadow-md' : ''
                            } ${isDraggingThis ? 'opacity-40 scale-95 border-dashed border-indigo-400' : ''}`}
                          >
                            <div className="flex items-center justify-between gap-1">
                              <span className="font-semibold truncate">
                                {a.course_name || a.course_id.slice(0, 8)}
                              </span>
                              {a.is_locked ? (
                                <Lock className="w-3 h-3 text-amber-600 shrink-0" title="Cell locked (FR-9.2)" />
                              ) : canDrag ? (
                                <Move className="w-3 h-3 text-slate-400 opacity-0 group-hover/card:opacity-100 shrink-0 transition-opacity" />
                              ) : null}
                            </div>

                            <div className="mt-0.5 opacity-75 truncate font-medium">
                              {a.staff_name || 'Faculty'}
                            </div>

                            <div className="mt-1 opacity-70 text-[10px] truncate flex justify-between items-center pt-1 border-t border-black/5">
                              <span>🚪 {a.room_name || 'Room'}</span>
                              {a.batch_id && <span className="bg-black/10 px-1 rounded">Batch</span>}
                            </div>
                          </div>
                        );
                      })}

                      {assignments.length === 0 && isOver && (
                        <div className="h-full flex items-center justify-center border-2 border-dashed border-indigo-300 rounded-lg text-indigo-500 text-xs font-medium bg-indigo-50/50">
                          Drop here
                        </div>
                      )}
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
