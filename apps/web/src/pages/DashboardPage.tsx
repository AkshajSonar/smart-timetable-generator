import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useTenant } from '../lib/TenantContext';
import { BarChart3, Users, Building2, BookOpen, CalendarDays, PlusCircle, FileCheck2, ChevronRight, Clock } from 'lucide-react';
import { Link } from 'react-router-dom';

export function DashboardPage() {
  const { tenantId, tenantName, termId, lastVersionId } = useTenant();
  
  const [metrics, setMetrics] = useState({
    courses: 0,
    faculty: 0,
    rooms: 0,
    students: 0
  });

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      if (!tenantId) return;
      try {
        const [courses, staff, rooms, students] = await Promise.all([
          api.courses.list(tenantId).catch(() => ({ items: [] })),
          api.staff.list(tenantId).catch(() => ({ items: [] })),
          api.rooms.list(tenantId).catch(() => ({ items: [] })),
          api.students.list(tenantId).catch(() => ({ items: [] }))
        ]);
        setMetrics({
          courses: courses.items.length,
          faculty: staff.items.length,
          rooms: rooms.items.length,
          students: students.items.length
        });
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [tenantId]);

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Welcome back, Alice 👋
          </h1>
          <p className="text-slate-500">
            {tenantName || 'Demo University'} — Overview for {termId || 'the active term'}
          </p>
        </div>
        <div className="flex gap-3">
          <Link to="/setup" className="bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 px-4 py-2 rounded-xl text-sm font-medium transition-colors shadow-sm">
            Institution Settings
          </Link>
          <Link to="/generate" className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors shadow-sm">
            <CalendarDays className="w-4 h-4" />
            Generate Timetable
          </Link>
        </div>
      </header>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-100 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center gap-4 mb-3">
            <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <BookOpen className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-2xl font-bold text-slate-900 leading-none">{loading ? '...' : metrics.courses}</h3>
              <p className="text-slate-500 font-medium text-sm mt-1">Classes</p>
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-100 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center gap-4 mb-3">
            <div className="w-12 h-12 rounded-xl bg-orange-50 text-orange-600 flex items-center justify-center">
              <PlusCircle className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-2xl font-bold text-slate-900 leading-none">0</h3>
              <p className="text-slate-500 font-medium text-sm mt-1">Conflicts</p>
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-100 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center gap-4 mb-3">
            <div className="w-12 h-12 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-2xl font-bold text-slate-900 leading-none">{loading ? '...' : metrics.faculty}</h3>
              <p className="text-slate-500 font-medium text-sm mt-1">Faculty</p>
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-100 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center gap-4 mb-3">
            <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Building2 className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-2xl font-bold text-slate-900 leading-none">{loading ? '...' : metrics.rooms}</h3>
              <p className="text-slate-500 font-medium text-sm mt-1">Rooms</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Col: Timetable */}
        <div className="lg:col-span-2 bg-white border border-slate-100 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-bold text-slate-900">This Week's Timetable</h2>
            <button className="text-sm font-medium text-indigo-600 hover:text-indigo-700">View Full</button>
          </div>
          
          <div className="w-full h-64 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-center relative overflow-hidden">
            {/* Mock mini timetable grid */}
            <div className="absolute inset-0 grid grid-cols-5 grid-rows-4 gap-1 p-2">
               {/* Day headers */}
               <div className="text-center text-xs font-medium text-slate-400">Mon</div>
               <div className="text-center text-xs font-medium text-slate-400">Tue</div>
               <div className="text-center text-xs font-medium text-slate-400">Wed</div>
               <div className="text-center text-xs font-medium text-slate-400">Thu</div>
               <div className="text-center text-xs font-medium text-slate-400">Fri</div>
               
               {/* Blocks */}
               <div className="bg-indigo-100 rounded-md p-1 border border-indigo-200"></div>
               <div className="bg-emerald-100 rounded-md p-1 border border-emerald-200"></div>
               <div className="bg-orange-100 rounded-md p-1 border border-orange-200"></div>
               <div className="bg-sky-100 rounded-md p-1 border border-sky-200"></div>
               <div className="bg-purple-100 rounded-md p-1 border border-purple-200"></div>

               <div></div>
               <div className="bg-sky-100 rounded-md p-1 border border-sky-200"></div>
               <div className="bg-indigo-100 rounded-md p-1 border border-indigo-200"></div>
               <div></div>
               <div className="bg-emerald-100 rounded-md p-1 border border-emerald-200"></div>

               <div className="bg-orange-100 rounded-md p-1 border border-orange-200"></div>
               <div></div>
               <div className="bg-purple-100 rounded-md p-1 border border-purple-200"></div>
               <div className="bg-emerald-100 rounded-md p-1 border border-emerald-200"></div>
               <div className="bg-indigo-100 rounded-md p-1 border border-indigo-200"></div>
            </div>
          </div>
        </div>

        {/* Right Col: Upcoming & Activity */}
        <div className="space-y-6">
          <div className="bg-white border border-slate-100 rounded-2xl p-6 shadow-sm">
            <h2 className="text-lg font-bold text-slate-900 mb-4">Upcoming</h2>
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-orange-50 flex items-center justify-center shrink-0 mt-0.5">
                  <div className="w-2 h-2 rounded-full bg-orange-500"></div>
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-900">Review draft timetable</p>
                  <p className="text-xs text-slate-500">Action Required</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-emerald-50 flex items-center justify-center shrink-0 mt-0.5">
                  <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-900">Add elective enrollments</p>
                  <p className="text-xs text-slate-500">Due tomorrow</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white border border-slate-100 rounded-2xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-slate-900">Recent Activity</h2>
            </div>
            <div className="space-y-4">
              <div className="flex gap-3 relative before:absolute before:left-[15px] before:top-8 before:bottom-[-16px] before:w-px before:bg-slate-200">
                <div className="w-8 h-8 rounded-full bg-slate-100 border-2 border-white flex items-center justify-center shrink-0 z-10">
                  <CalendarDays className="w-4 h-4 text-slate-500" />
                </div>
                <div>
                  <p className="text-sm text-slate-900 font-medium">Timetable generated</p>
                  <p className="text-xs text-slate-500">2 hours ago</p>
                </div>
              </div>
              
              <div className="flex gap-3 relative">
                <div className="w-8 h-8 rounded-full bg-slate-100 border-2 border-white flex items-center justify-center shrink-0 z-10">
                  <Users className="w-4 h-4 text-slate-500" />
                </div>
                <div>
                  <p className="text-sm text-slate-900 font-medium">New faculty added</p>
                  <p className="text-xs text-slate-500">Yesterday</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
