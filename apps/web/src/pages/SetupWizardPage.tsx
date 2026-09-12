import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, GraduationCap, Library, ArrowRight, CheckCircle2, Upload, FileSpreadsheet, Download, AlertCircle, Loader2 } from 'lucide-react';
import { useTenant } from '../lib/TenantContext';
import { api } from '../api/client';

export function SetupWizardPage() {
  const navigate = useNavigate();
  const { tenantId } = useTenant();
  const [step, setStep] = useState(1);
  const [institutionType, setInstitutionType] = useState<string | null>('college');
  const [campusName, setCampusName] = useState('Main Campus');
  const [uploading, setUploading] = useState<string | null>(null);
  const [importResults, setImportResults] = useState<Record<string, { success_count: number; errors: any[] }>>({});

  const downloadSampleCsv = (type: string) => {
    let csvData = '';
    let filename = '';

    if (type === 'faculty') {
      csvData = 'external_id,full_name,email,workload_cap_week,workload_cap_day,employment_type\nF001,Dr. Alan Turing,turing@inst.edu,20,5,full_time\nF002,Prof. Ada Lovelace,lovelace@inst.edu,24,6,full_time';
      filename = 'faculty.csv';
    } else if (type === 'courses') {
      csvData = 'code,name,department,type,hours_per_week,block_size\nCS101,Algorithms & Data Structures,Computer Science,core,4,1\nCS102,Database Systems Lab,Computer Science,lab,3,2';
      filename = 'courses.csv';
    } else if (type === 'rooms') {
      csvData = 'name,building,room_type,capacity,equipment_tags\nHall A,Science Block,lecture_hall,120,"projector,ac"\nLab 101,IT Block,lab,30,"computers,lab_kit"';
      filename = 'rooms.csv';
    } else if (type === 'enrollment') {
      csvData = 'student_external_id,elective_section_external_id\nSTU001,ELEC_SEC_01\nSTU002,ELEC_SEC_02';
      filename = 'enrollment.csv';
    }

    const blob = new Blob([csvData], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleFileUpload = async (type: 'faculty' | 'courses' | 'rooms' | 'enrollments', file: File) => {
    if (!tenantId) return;
    setUploading(type);
    try {
      const text = await file.text();
      const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
      if (lines.length <= 1) {
        alert("CSV file is empty or missing headers");
        return;
      }
      
      const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
      const rows: any[] = [];

      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',').map(v => v.trim().replace(/^"|"$/g, ''));
        const rowObj: Record<string, any> = {};
        headers.forEach((h, idx) => {
          rowObj[h] = values[idx] ?? '';
        });
        
        // Type coercion
        if (rowObj.workload_cap_week) rowObj.workload_cap_week = parseInt(rowObj.workload_cap_week) || 20;
        if (rowObj.workload_cap_day) rowObj.workload_cap_day = parseInt(rowObj.workload_cap_day) || 6;
        if (rowObj.hours_per_week) rowObj.hours_per_week = parseInt(rowObj.hours_per_week) || 3;
        if (rowObj.block_size) rowObj.block_size = parseInt(rowObj.block_size) || 1;
        if (rowObj.capacity) rowObj.capacity = parseInt(rowObj.capacity) || 60;
        if (rowObj.equipment_tags && typeof rowObj.equipment_tags === 'string') {
          rowObj.equipment_tags = rowObj.equipment_tags.split(';').map((s: string) => s.trim()).filter(Boolean);
        }

        rows.push(rowObj);
      }

      let res: { success_count: number; errors: any[] };
      if (type === 'faculty') {
        res = await api.import.faculty(tenantId, rows);
      } else if (type === 'courses') {
        res = await api.import.courses(tenantId, rows);
      } else if (type === 'rooms') {
        res = await api.import.rooms(tenantId, rows);
      } else {
        res = await api.import.enrollments(tenantId, rows);
      }

      setImportResults(prev => ({ ...prev, [type]: res }));
    } catch (err: any) {
      alert(`Import failed: ${err.message}`);
    } finally {
      setUploading(null);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8">
      <header className="mb-10">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-2">Institution & Data Setup</h1>
        <p className="text-slate-500 text-lg">Configure your scheduling environment and import master data.</p>
      </header>

      {/* Stepper Tabs */}
      <div className="flex items-center gap-2 mb-8">
        <div className={`flex items-center gap-2 ${step >= 1 ? 'text-indigo-600' : 'text-slate-400'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${step >= 1 ? 'bg-indigo-100' : 'bg-slate-100'}`}>1</div>
          <span className="font-medium text-sm">Institution Type</span>
        </div>
        <div className="w-12 h-px bg-slate-200"></div>
        <div className={`flex items-center gap-2 ${step >= 2 ? 'text-indigo-600' : 'text-slate-400'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${step >= 2 ? 'bg-indigo-100' : 'bg-slate-100'}`}>2</div>
          <span className="font-medium text-sm">Campus Setup</span>
        </div>
        <div className="w-12 h-px bg-slate-200"></div>
        <div className={`flex items-center gap-2 ${step >= 3 ? 'text-indigo-600' : 'text-slate-400'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${step >= 3 ? 'bg-indigo-100' : 'bg-slate-100'}`}>3</div>
          <span className="font-medium text-sm">Bulk Imports (FR-2.2, FR-3.1)</span>
        </div>
      </div>

      {step === 1 && (
        <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm">
          <h2 className="text-xl font-bold text-slate-900 mb-6">Select your institution type</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            {[
              { id: 'school', title: 'School', desc: 'K-12 institutions', icon: Building2 },
              { id: 'college', title: 'College', desc: 'Undergraduate colleges', icon: GraduationCap },
              { id: 'university', title: 'University', desc: 'Multi-department universities', icon: Library },
            ].map(type => (
              <button
                key={type.id}
                onClick={() => setInstitutionType(type.id)}
                className={`relative flex flex-col items-center text-center p-6 rounded-xl border-2 transition-all ${
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

          <div className="flex justify-end pt-6 border-t border-slate-100">
            <button 
              onClick={() => setStep(2)}
              disabled={!institutionType}
              className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-colors shadow-sm"
            >
              Next: Campus Setup <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm space-y-6">
          <h2 className="text-xl font-bold text-slate-900">Campus details</h2>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Primary Campus Name</label>
            <input 
              type="text" 
              value={campusName}
              onChange={(e) => setCampusName(e.target.value)}
              className="w-full max-w-md bg-white border border-slate-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>

          <div className="flex justify-between pt-6 border-t border-slate-100">
            <button onClick={() => setStep(1)} className="text-slate-500 hover:text-slate-700 font-medium text-sm">
              Back
            </button>
            <button 
              onClick={() => setStep(3)}
              className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-colors shadow-sm"
            >
              Next: Master Data Imports <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm space-y-6">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Bulk Master Data & Enrollment Imports</h2>
            <p className="text-slate-500 text-sm">Upload CSV files for faculty, courses, rooms, and elective enrollments per §29.4 standards.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[
              { key: 'faculty', title: 'Faculty CSV Import (FR-2.2)', template: 'faculty' },
              { key: 'courses', title: 'Courses CSV Import (FR-2.2)', template: 'courses' },
              { key: 'rooms', title: 'Rooms & Labs CSV (FR-2.2)', template: 'rooms' },
              { key: 'enrollments', title: 'Elective Enrollments (FR-3.1)', template: 'enrollment' },
            ].map(item => (
              <div key={item.key} className="border border-slate-200 rounded-xl p-5 bg-slate-50/50 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
                    <FileSpreadsheet className="w-4 h-4 text-indigo-600" />
                    {item.title}
                  </div>
                  <button
                    onClick={() => downloadSampleCsv(item.template)}
                    className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 font-medium"
                  >
                    <Download className="w-3.5 h-3.5" /> Sample CSV
                  </button>
                </div>

                <label className="flex flex-col items-center justify-center border-2 border-dashed border-slate-200 rounded-xl p-4 bg-white hover:bg-slate-50 cursor-pointer transition-colors">
                  {uploading === item.key ? (
                    <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
                  ) : (
                    <>
                      <Upload className="w-6 h-6 text-slate-400 mb-1" />
                      <span className="text-xs font-medium text-slate-700">Click to upload {item.key}.csv</span>
                    </>
                  )}
                  <input
                    type="file"
                    accept=".csv"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files?.[0]) {
                        handleFileUpload(item.key as any, e.target.files[0]);
                      }
                    }}
                  />
                </label>

                {importResults[item.key] && (
                  <div className={`p-3 rounded-lg text-xs space-y-1 ${
                    importResults[item.key].errors.length > 0 ? 'bg-amber-50 text-amber-900 border border-amber-200' : 'bg-emerald-50 text-emerald-900 border border-emerald-200'
                  }`}>
                    <div className="font-semibold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      Successfully imported {importResults[item.key].success_count} records.
                    </div>
                    {importResults[item.key].errors.map((err, i) => (
                      <div key={i} className="text-rose-700 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3 shrink-0" />
                        {err.row}: {err.error}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="flex justify-between pt-6 border-t border-slate-100">
            <button onClick={() => setStep(2)} className="text-slate-500 hover:text-slate-700 font-medium text-sm">
              Back
            </button>
            <button
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-colors shadow-sm"
            >
              Complete Setup <CheckCircle2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
