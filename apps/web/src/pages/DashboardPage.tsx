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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm transition-all hover:shadow-md">
          <div className="flex justify-between items-start mb-4">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <BookOpen className="w-5 h-5" />
            </div>
            <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md">+2 new</span>
          </div>
          <p className="text-slate-500 font-medium text-sm mb-1">Total Courses</p>
          <h3 className="text-3xl font-bold text-slate-900">{loading ? '...' : metrics.courses}</h3>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm transition-all hover:shadow-md">
          <div className="flex justify-between items-start mb-4">
            <div className="w-10 h-10 rounded-xl bg-violet-50 text-violet-600 flex items-center justify-center">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <p className="text-slate-500 font-medium text-sm mb-1">Active Faculty</p>
          <h3 className="text-3xl font-bold text-slate-900">{loading ? '...' : metrics.faculty}</h3>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm transition-all hover:shadow-md">
          <div className="flex justify-between items-start mb-4">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Building2 className="w-5 h-5" />
            </div>
          </div>
          <p className="text-slate-500 font-medium text-sm mb-1">Total Rooms & Labs</p>
          <h3 className="text-3xl font-bold text-slate-900">{loading ? '...' : metrics.rooms}</h3>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm transition-all hover:shadow-md">
          <div className="flex justify-between items-start mb-4">
            <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <BarChart3 className="w-5 h-5" />
            </div>
          </div>
          <p className="text-slate-500 font-medium text-sm mb-1">Registered Students</p>
          <h3 className="text-3xl font-bold text-slate-900">{loading ? '...' : metrics.students}</h3>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-bold text-slate-900">Quick Actions</h2>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Link to="/rules" className="flex flex-col items-center justify-center p-6 bg-slate-50 border border-slate-100 rounded-xl hover:bg-slate-100 transition-colors group cursor-pointer text-center">
              <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center shadow-sm mb-3 group-hover:scale-110 transition-transform">
                <PlusCircle className="w-6 h-6 text-indigo-600" />
              </div>
              <span className="font-medium text-slate-900">Add Constraint Rule</span>
            </Link>
            <Link to="/review" className="flex flex-col items-center justify-center p-6 bg-slate-50 border border-slate-100 rounded-xl hover:bg-slate-100 transition-colors group cursor-pointer text-center">
              <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center shadow-sm mb-3 group-hover:scale-110 transition-transform">
                <FileCheck2 className="w-6 h-6 text-emerald-600" />
              </div>
              <span className="font-medium text-slate-900">Review Draft Timetable</span>
            </Link>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-bold text-slate-900">Recent Activity</h2>
            <button className="text-sm font-medium text-indigo-600 hover:text-indigo-700">View All</button>
          </div>
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="w-10 h-10 rounded-full bg-indigo-50 flex items-center justify-center shrink-0">
                <CalendarDays className="w-5 h-5 text-indigo-600" />
              </div>
              <div>
                <p className="text-sm text-slate-900 font-medium">Draft Timetable v2 Generated</p>
                <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
                  <Clock className="w-3.5 h-3.5" />
                  <span>2 hours ago by System</span>
                </div>
              </div>
            </div>
            
            <div className="flex gap-4">
              <div className="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center shrink-0">
                <FileCheck2 className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-sm text-slate-900 font-medium">New rule added for CS301</p>
                <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
                  <Clock className="w-3.5 h-3.5" />
                  <span>Yesterday by Alice</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
