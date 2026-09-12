import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Calendar, 
  Settings, 
  Users, 
  BookOpen, 
  ListChecks, 
  FileCheck2, 
  Upload,
  UserCheck,
  BarChart3,
  CalendarCheck2,
  LogOut,
  Building2,
  GraduationCap
} from 'lucide-react';

const mainNavItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/setup', label: 'Setup Wizard', icon: Settings },
  { path: '/courses', label: 'Courses', icon: BookOpen },
  { path: '/faculty', label: 'Faculty', icon: Users },
  { path: '/rooms', label: 'Rooms & Labs', icon: Building2 },
];

const generationItems = [
  { path: '/rules', label: 'Rules & Constraints', icon: ListChecks },
  { path: '/generate', label: 'Generate Timetable', icon: Calendar },
  { path: '/review', label: 'Review Timetable', icon: FileCheck2 },
  { path: '/publish', label: 'Publish Timetable', icon: Upload },
];

const specializedItems = [
  { path: '/timetable', label: 'Timetable (Cohort)', icon: CalendarCheck2 },
  { path: '/exams', label: 'Exams', icon: GraduationCap },
  { path: '/substitutions', label: 'Substitutions', icon: UserCheck },
  { path: '/reports', label: 'Reports & Analytics', icon: BarChart3 },
  { path: '/student-view', label: 'My Schedule', icon: Calendar },
];

import { useNavigate } from 'react-router-dom';

export function Sidebar() {
  const navigate = useNavigate();
  const NavItem = ({ item }: { item: { path: string, label: string, icon: any } }) => (
    <NavLink
      to={item.path}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-200 group ${
          isActive 
            ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20' 
            : 'text-slate-400 hover:text-white hover:bg-slate-800'
        }`
      }
    >
      <item.icon className="w-5 h-5 shrink-0" />
      <span className="font-medium text-sm truncate">{item.label}</span>
    </NavLink>
  );

  return (
    <aside className="w-64 h-screen bg-[#111827] flex flex-col border-r border-slate-800 shrink-0 sticky top-0 overflow-y-auto overflow-x-hidden">
      <div className="p-5 flex items-center gap-3 shrink-0">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <span className="text-white font-bold text-lg leading-none">S</span>
        </div>
        <span className="text-white font-bold text-xl tracking-tight">Schedulr</span>
      </div>

      <div className="flex-1 px-3 py-2 space-y-6">
        <div>
          <div className="px-3 mb-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">Core</div>
          <div className="space-y-1">
            {mainNavItems.map(item => <NavItem key={item.path} item={item} />)}
          </div>
        </div>

        <div>
          <div className="px-3 mb-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">Generation</div>
          <div className="space-y-1">
            {generationItems.map(item => <NavItem key={item.path} item={item} />)}
          </div>
        </div>

        <div>
          <div className="px-3 mb-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">Views</div>
          <div className="space-y-1">
            {specializedItems.map(item => <NavItem key={item.path} item={item} />)}
          </div>
        </div>
      </div>

      <div className="p-4 shrink-0 border-t border-slate-800">
        <button 
          onClick={() => {
            localStorage.clear();
            navigate('/login');
          }}
          className="flex items-center gap-3 px-3 py-2 w-full rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <LogOut className="w-5 h-5" />
          <span className="font-medium text-sm">Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
