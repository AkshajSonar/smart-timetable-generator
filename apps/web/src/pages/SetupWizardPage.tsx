import { useState } from 'react';
import { Building2, GraduationCap, Library, ArrowRight, CheckCircle2 } from 'lucide-react';

export function SetupWizardPage() {
  const [step, setStep] = useState(1);
  const [institutionType, setInstitutionType] = useState<string | null>(null);

  return (
    <div className="max-w-4xl mx-auto py-8">
      <header className="mb-12">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-2">Institution Setup</h1>
        <p className="text-slate-500 text-lg">Let's set up your scheduling environment.</p>
      </header>

      <div className="flex gap-12">
        {/* Left Form Area */}
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-8">
            <div className={`flex items-center gap-2 ${step >= 1 ? 'text-indigo-600' : 'text-slate-400'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${step >= 1 ? 'bg-indigo-100' : 'bg-slate-100'}`}>1</div>
              <span className="font-medium text-sm">Institution</span>
            </div>
            <div className="w-8 h-px bg-slate-200"></div>
            <div className={`flex items-center gap-2 ${step >= 2 ? 'text-indigo-600' : 'text-slate-400'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${step >= 2 ? 'bg-indigo-100' : 'bg-slate-100'}`}>2</div>
              <span className="font-medium text-sm">Campus</span>
            </div>
            <div className="w-8 h-px bg-slate-200"></div>
            <div className="flex items-center gap-2 text-slate-400">
              <div className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm bg-slate-100">3</div>
              <span className="font-medium text-sm">Modules</span>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm">
            <h2 className="text-xl font-bold text-slate-900 mb-6">Select your institution type</h2>
            
            <div className="grid grid-cols-3 gap-4 mb-8">
              {[
                { id: 'school', title: 'School', desc: 'K-12 institutions', icon: Building2 },
                { id: 'college', title: 'College', desc: 'Undergraduate colleges', icon: GraduationCap },
                { id: 'university', title: 'University', desc: 'Multi-department universities', icon: Library },
              ].map(type => (
                <button
                  key={type.id}
                  onClick={() => setInstitutionType(type.id)}
                  className={`flex flex-col items-center text-center p-6 rounded-xl border-2 transition-all ${
                    institutionType === type.id 
                      ? 'border-indigo-600 bg-indigo-50/50' 
                      : 'border-slate-100 hover:border-slate-200 bg-white'
                  }`}
                >
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center mb-4 ${
                    institutionType === type.id ? 'bg-indigo-100 text-indigo-600' : 'bg-slate-50 text-slate-400'
                  }`}>
                    <type.icon className="w-6 h-6" />
                  </div>
                  <h3 className={`font-bold mb-1 ${institutionType === type.id ? 'text-indigo-900' : 'text-slate-700'}`}>{type.title}</h3>
                  <p className="text-xs text-slate-500">{type.desc}</p>
                  
                  {institutionType === type.id && (
                    <div className="absolute top-3 right-3 text-indigo-600">
                      <CheckCircle2 className="w-5 h-5" />
                    </div>
                  )}
                </button>
              ))}
            </div>

            <div className="flex justify-between items-center pt-6 border-t border-slate-100">
              <button className="text-slate-500 hover:text-slate-700 font-medium text-sm">
                Back
              </button>
              <button 
                onClick={() => setStep(2)}
                disabled={!institutionType}
                className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-200 disabled:text-slate-400 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-colors shadow-sm"
              >
                Next Step
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Right Graphic Area */}
        <div className="hidden lg:flex w-72 flex-col items-center text-center mt-12">
          <div className="w-full aspect-square bg-indigo-50 rounded-full flex items-center justify-center mb-6 relative">
            <div className="absolute inset-0 bg-gradient-to-tr from-indigo-100 to-purple-50 rounded-full mix-blend-multiply opacity-50"></div>
            <Building2 className="w-32 h-32 text-indigo-600 relative z-10" strokeWidth={1} />
          </div>
          <h3 className="text-xl font-bold text-slate-900 mb-2">Let's set up your institution</h3>
          <p className="text-slate-500 text-sm">A few quick steps to tailor Schedulr exactly to your needs.</p>
        </div>
      </div>
    </div>
  );
}
