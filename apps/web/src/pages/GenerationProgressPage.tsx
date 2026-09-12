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
    <div className="max-w-2xl mx-auto py-12 flex flex-col items-center justify-center min-h-[70vh]">
      <div className="w-24 h-24 bg-indigo-50 rounded-full flex items-center justify-center mb-8 relative">
        <div className="absolute inset-0 bg-indigo-400 rounded-full animate-ping opacity-20"></div>
        <Bot className="w-12 h-12 text-indigo-600 relative z-10 animate-bounce" />
      </div>

      <h2 className="text-2xl font-bold tracking-tight text-slate-900 mb-2">
        {error ? 'Generation Failed' : 'Generating Timetable...'}
      </h2>
      
      {error ? (
        <div className="mt-6 p-4 bg-rose-50 text-rose-700 rounded-xl border border-rose-200 text-center w-full">
          <p className="font-medium">{error}</p>
          <button 
            onClick={() => navigate('/generate')}
            className="mt-4 bg-rose-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-rose-700"
          >
            Go Back
          </button>
        </div>
      ) : (
        <p className="text-slate-500 mb-12">Please wait while our AI engine crunches the numbers.</p>
      )}

      {!error && (
        <div className="w-full max-w-md space-y-4">
          {steps.map((step, index) => {
            const isActive = index === currentStep;
            const isPast = index < currentStep;
            
            return (
              <div key={index} className={`flex items-center gap-4 transition-all duration-500 ${
                isActive ? 'opacity-100 scale-105 transform' : 
                isPast ? 'opacity-50' : 'opacity-20'
              }`}>
                {isPast ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                ) : isActive ? (
                  <div className="w-5 h-5 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin"></div>
                ) : (
                  <div className="w-5 h-5 rounded-full border-2 border-slate-300"></div>
                )}
                <span className={`font-medium ${
                  isActive ? 'text-indigo-900' : 'text-slate-600'
                }`}>
                  {step}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
