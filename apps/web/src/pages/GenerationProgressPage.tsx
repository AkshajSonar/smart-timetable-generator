import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot, CheckCircle2 } from 'lucide-react';
import { api } from '../api/client';
import { useTenant } from '../lib/TenantContext';

const steps = [
  'Parsing constraints...',
  'Checking faculty availability...',
  'Mapping cohorts and batches...',
  'Resolving hard constraints...',
  'Optimizing soft constraints...',
  'Finalizing timetable...'
];

export function GenerationProgressPage() {
  const navigate = useNavigate();
  const { tenantId, termId, setLastVersionId } = useTenant();
  const [currentStep, setCurrentStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Simulate step progression purely for UX
    const interval = setInterval(() => {
      setCurrentStep(prev => (prev < steps.length - 1 ? prev + 1 : prev));
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    let mounted = true;

    async function doGeneration() {
      if (!tenantId || !termId) return;
      try {
        const response = await api.timetables.generate(tenantId, termId);
        
        if (!mounted) return;
        
        setLastVersionId(response.timetable_version_id);
        
        // Ensure minimum 5 seconds of loading animation for UX before redirecting
        setTimeout(() => {
          if (mounted) navigate('/review');
        }, 5000);
        
      } catch (err: unknown) {
        if (!mounted) return;
        setError((err as Error).message);
      }
    }

    doGeneration();

    return () => { mounted = false; };
  }, [tenantId, termId, navigate, setLastVersionId]);

  return (
    <div className="max-w-5xl mx-auto py-12 flex flex-col md:flex-row items-center justify-center min-h-[70vh] gap-12">
      
      {/* Left Image Section */}
      <div className="flex-1 flex flex-col items-center text-center">
        <img 
          src="/lightbulb.png" 
          alt="AI processing" 
          className="w-full max-w-[280px] drop-shadow-2xl mb-8 animate-pulse-slow"
        />
        <h2 className="text-3xl font-black tracking-tight text-slate-900 mb-4">
          {error ? 'Generation Failed' : 'Generating Timetable...'}
        </h2>
        
        {error ? (
          <div className="mt-2 p-4 bg-rose-50 text-rose-700 rounded-xl border border-rose-200 text-center w-full max-w-md">
            <p className="font-medium">{error}</p>
            <button 
              onClick={() => navigate('/generate')}
              className="mt-4 bg-rose-600 text-white px-6 py-2.5 rounded-xl text-sm font-medium hover:bg-rose-700 transition-colors shadow-sm"
            >
              Go Back
            </button>
          </div>
        ) : (
          <p className="text-slate-500 font-medium max-w-sm">Please wait while our AI engine crunches the numbers and resolves constraints.</p>
        )}
      </div>

      {/* Right Steps Section */}
      {!error && (
        <div className="flex-1 w-full max-w-md bg-white border border-slate-100 rounded-3xl p-8 shadow-sm">
          <div className="space-y-6">
            {steps.map((step, index) => {
              const isActive = index === currentStep;
              const isPast = index < currentStep;
              
              return (
                <div key={index} className={`flex items-center gap-4 transition-all duration-500 ${
                  isActive ? 'opacity-100 scale-105 transform translate-x-2' : 
                  isPast ? 'opacity-50' : 'opacity-20'
                }`}>
                  {isPast ? (
                    <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
                      <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    </div>
                  ) : isActive ? (
                    <div className="w-8 h-8 rounded-full bg-indigo-50 border-2 border-indigo-600 border-t-transparent animate-spin shrink-0"></div>
                  ) : (
                    <div className="w-8 h-8 rounded-full border-2 border-slate-200 bg-slate-50 shrink-0"></div>
                  )}
                  <span className={`font-medium ${
                    isActive ? 'text-indigo-900 text-lg' : 'text-slate-600'
                  }`}>
                    {step}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
