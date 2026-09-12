import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TenantProvider } from '../../lib/TenantContext';
import { Search, Bell } from 'lucide-react';

export function MainLayout() {
  const userName = localStorage.getItem('schedulr_user_name') || 'User';
  const userRole = localStorage.getItem('schedulr_user_role') || 'Guest';
  
  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900 font-sans">
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen relative max-w-full overflow-hidden">
        {/* Top Header */}
        <header className="h-16 px-8 flex items-center justify-between border-b border-slate-200 bg-white sticky top-0 z-10 shrink-0 shadow-sm shadow-slate-200/50">
          <div className="flex-1 max-w-xl">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input 
                type="text" 
                placeholder="Search anything..." 
                className="w-full bg-slate-50 border border-slate-200 rounded-full pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all placeholder:text-slate-400"
              />
            </div>
          </div>
          <div className="flex items-center gap-4 pl-4">
            <button className="p-2 text-slate-400 hover:text-slate-600 transition-colors relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full border-2 border-white"></span>
            </button>
            <div className="flex items-center gap-2 pl-4 border-l border-slate-200 cursor-pointer group">
              <div className="w-8 h-8 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center font-bold text-sm">
                {userName.charAt(0).toUpperCase()}
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-medium text-slate-700 group-hover:text-indigo-600 transition-colors leading-none">{userName}</span>
                <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider mt-0.5">{userRole}</span>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto p-8 bg-slate-50">
          <div className="max-w-7xl mx-auto w-full">
            <TenantProvider>
              <Outlet />
            </TenantProvider>
          </div>
        </main>
      </div>
    </div>
  );
}
