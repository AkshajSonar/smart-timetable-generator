import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TenantProvider } from '../../lib/TenantContext';
import { Search } from 'lucide-react';
import { NotificationDrawer } from '../notifications/NotificationDrawer';

export function MainLayout() {
  const userName = localStorage.getItem('schedulr_user_name') || 'User';
  const userRole = localStorage.getItem('schedulr_user_role') || 'Guest';
  
  return (
    <TenantProvider>
      <div className="flex min-h-screen bg-slate-50 text-slate-900 font-sans">
        <Sidebar />
        <div className="flex-1 flex flex-col min-h-screen relative max-w-full overflow-hidden">
          {/* Top Header */}
          <header className="h-16 px-8 flex items-center justify-between border-b border-slate-200 bg-white sticky top-0 z-10 shrink-0">
            {/* Empty div for spacing if we want centered search, but let's just use flex-1 */}
            <div className="flex-1 flex justify-center">
              <div className="relative group w-full max-w-md">
                <Search className="w-4 h-4 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2 group-focus-within:text-indigo-500 transition-colors" />
                <input 
                  type="text" 
                  placeholder="Search anything..." 
                  className="w-full bg-slate-50 border border-slate-200 rounded-full pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all placeholder:text-slate-400 text-slate-700"
                />
              </div>
            </div>
            
            <div className="flex items-center gap-4 pl-4 shrink-0">
              <NotificationDrawer />
              
              <div className="flex items-center gap-2 pl-4 border-l border-slate-200 cursor-pointer group">
                <img 
                  src="https://ui-avatars.com/api/?name=Admin&background=4F46E5&color=fff&rounded=true&bold=true" 
                  alt="Admin" 
                  className="w-8 h-8 rounded-full"
                />
                <span className="text-sm font-medium text-slate-700 group-hover:text-indigo-600 transition-colors">Admin</span>
              </div>
            </div>
          </header>

          {/* Main Content Area */}
          <main className="flex-1 overflow-y-auto p-8 bg-slate-50">
            <div className="max-w-7xl mx-auto w-full">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </TenantProvider>
  );
}
