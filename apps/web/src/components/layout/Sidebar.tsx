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
  { path: '/department-view', label: 'Department View', icon: Building2 },
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
      title={item.label}
      className={({ isActive }) =>
        `flex items-center justify-center w-12 h-12 rounded-xl transition-all duration-200 group mx-auto mb-2 ${
          isActive 
            ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/30' 
            : 'text-slate-400 hover:text-white hover:bg-slate-800'
        }`
      }
    >
      <item.icon className="w-5 h-5 shrink-0" />
    </NavLink>
  );

  return (
    <aside className="w-20 h-screen bg-[#1A1C29] flex flex-col shrink-0 sticky top-0 overflow-y-auto overflow-x-hidden z-20">
      <div className="p-4 flex items-center justify-center shrink-0 mb-6 mt-2">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30 cursor-pointer" title="Schedulr">
          <span className="text-white font-black text-2xl leading-none">S</span>
        </div>
      </div>

      <div className="flex-1 px-2 py-2 flex flex-col gap-1">
        {mainNavItems.map(item => <NavItem key={item.path} item={item} />)}
        <div className="w-8 h-px bg-slate-800 mx-auto my-2" />
        {generationItems.map(item => <NavItem key={item.path} item={item} />)}
        <div className="w-8 h-px bg-slate-800 mx-auto my-2" />
        {specializedItems.map(item => <NavItem key={item.path} item={item} />)}
      </div>

      <div className="p-4 shrink-0 mt-auto">
        <button 
          title="Sign Out"
          onClick={() => {
            localStorage.clear();
            navigate('/login');
          }}
          className="flex items-center justify-center w-12 h-12 mx-auto rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <LogOut className="w-5 h-5" />
        </button>
      </div>
    </aside>
  );
}
