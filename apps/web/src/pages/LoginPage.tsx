import { useNavigate } from 'react-router-dom';
import { Mail, Lock, CalendarDays } from 'lucide-react';

import { setBearerToken } from '../api/client';

export function LoginPage() {
  const navigate = useNavigate();

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    
    const form = e.target as HTMLFormElement;
    const email = (form.elements[0] as HTMLInputElement).value.toLowerCase();
    
    let token = 'demo-6c5a2d06-025b-4fd6-958f-859eff1fb687'; // Default to admin
    let name = 'Alice Admin';
    let role = 'Admin';
    
    if (email.includes('reviewer')) {
      token = 'demo-68d34996-3dc3-49bf-a9c3-71741d5734b0';
      name = 'Rachel Reviewer';
      role = 'Reviewer';
    } else if (email.includes('faculty') || email.includes('head')) {
      token = 'demo-a061fc56-a471-4fd9-8c52-bf762b938722';
      name = 'Frank Faculty';
      role = 'Faculty';
    } else if (email.includes('student')) {
      token = 'demo-0822a6aa-1cfc-43a9-a9c1-80476abf87a9';
      name = 'Sally Student';
      role = 'Student';
    }

    setBearerToken(token);
    localStorage.setItem('schedulr_user_name', name);
    localStorage.setItem('schedulr_user_role', role);
    
    navigate('/dashboard'); 
  };

  return (
    <div className="min-h-screen flex w-full bg-white text-slate-900 font-sans">
      
      {/* Left Form Section */}
      <div className="flex-1 flex flex-col justify-center px-12 sm:px-24 lg:px-32 max-w-2xl relative z-10 bg-white">
        
        <div className="flex items-center gap-2 mb-16">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <span className="text-white font-bold text-lg leading-none">S</span>
          </div>
          <span className="font-bold text-2xl tracking-tight">Schedulr</span>
        </div>

        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight mb-2">Smart Timetable Generator for Smarter Institutions</h1>
        </div>

        <form onSubmit={handleLogin} className="space-y-5">
          <div className="space-y-1 relative">
            <Mail className="w-5 h-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
            <input 
              type="email" 
              placeholder="Email" 
              className="w-full pl-12 pr-4 py-3 rounded-xl bg-slate-50 border border-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all placeholder:text-slate-400"
              required
            />
          </div>
          
          <div className="space-y-1 relative">
            <Lock className="w-5 h-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
            <input 
              type="password" 
              placeholder="Password" 
              className="w-full pl-12 pr-4 py-3 rounded-xl bg-slate-50 border border-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all placeholder:text-slate-400"
              required
            />
          </div>

          <div className="flex items-center justify-between text-sm mt-4">
            <label className="flex items-center gap-2 cursor-pointer text-slate-600">
              <input type="checkbox" className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-600" />
              Remember me
            </label>
            <a href="#" className="text-indigo-600 hover:text-indigo-700 font-medium transition-colors">Forgot password?</a>
          </div>

          <button 
            type="submit" 
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 rounded-xl transition-all shadow-lg shadow-indigo-600/20 mt-6"
          >
            Sign In
          </button>
        </form>

        <div className="mt-8 flex items-center gap-4 before:flex-1 before:border-t before:border-slate-200 after:flex-1 after:border-t after:border-slate-200">
          <span className="text-sm text-slate-400 font-medium">or continue with</span>
        </div>

        <div className="mt-8 flex flex-col gap-3">
          <button 
            type="button"
            onClick={() => {
              const form = document.querySelector('form');
              if(form) (form.elements[0] as HTMLInputElement).value = 'admin@timetable.local';
            }}
            className="text-xs font-medium text-slate-500 hover:text-indigo-600 transition-colors text-left"
          >
            Demo: admin@timetable.local
          </button>
          <button 
            type="button"
            onClick={() => {
              const form = document.querySelector('form');
              if(form) (form.elements[0] as HTMLInputElement).value = 'reviewer@timetable.local';
            }}
            className="text-xs font-medium text-slate-500 hover:text-indigo-600 transition-colors text-left"
          >
            Demo: reviewer@timetable.local
          </button>
        </div>
        
        <p className="mt-12 text-center text-sm text-slate-500">
          New to Schedulr? <a href="#" className="text-indigo-600 font-medium hover:underline">Contact your admin</a>
        </p>

      </div>

      {/* Right Graphic Section */}
      <div className="hidden lg:flex flex-1 relative bg-indigo-50/50 overflow-hidden items-center justify-center p-12">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-100 to-purple-50 mix-blend-multiply opacity-50"></div>
        
        <div className="relative z-10 w-full h-full max-w-2xl text-center flex flex-col justify-center items-center">
          <h2 className="text-5xl font-black tracking-tight text-slate-900 mb-2 drop-shadow-sm">
            Organize.<br/>Optimize.<br/><span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600">Empower.</span>
          </h2>
          <p className="text-xl text-slate-600 font-medium mb-12">Better schedules, brighter futures.</p>
          
          <img 
            src="/login_hero.png" 
            alt="Student organizing schedule" 
            className="w-full h-auto object-contain drop-shadow-2xl max-h-[60vh]"
          />
        </div>
      </div>

    </div>
  );
}
