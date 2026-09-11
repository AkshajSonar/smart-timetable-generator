import { useState } from 'react';
import { GeneratePage } from './pages/GeneratePage';
import { StudentViewPage } from './features/faculty-student-view/StudentViewPage';
import { ExamViews } from './features/exam-module/ExamViews';
import { PublishPage } from './features/publish/PublishPage';
import { RuleBuilderPage } from './features/rule-builder/RuleBuilderPage';
import './App.css';

function App() {
  const [currentTab, setCurrentTab] = useState<'generate' | 'students' | 'exams' | 'publish' | 'rules'>('generate');

  return (
    <div className="min-h-screen bg-slate-950 p-8 flex flex-col gap-6">
      <nav className="max-w-6xl mx-auto w-full flex gap-4 border-b border-white/10 pb-4 overflow-x-auto">
        <button
          onClick={() => setCurrentTab('generate')}
          className={`whitespace-nowrap px-4 py-2 rounded-lg font-medium transition-colors ${currentTab === 'generate' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
        >
          Generate / Reports
        </button>
        <button
          onClick={() => setCurrentTab('publish')}
          className={`whitespace-nowrap px-4 py-2 rounded-lg font-medium transition-colors ${currentTab === 'publish' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
        >
          Review & Publish
        </button>
        <button
          onClick={() => setCurrentTab('rules')}
          className={`whitespace-nowrap px-4 py-2 rounded-lg font-medium transition-colors ${currentTab === 'rules' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
        >
          Rule Builder
        </button>
        <button
          onClick={() => setCurrentTab('students')}
          className={`whitespace-nowrap px-4 py-2 rounded-lg font-medium transition-colors ${currentTab === 'students' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
        >
          Student View
        </button>
        <button
          onClick={() => setCurrentTab('exams')}
          className={`whitespace-nowrap px-4 py-2 rounded-lg font-medium transition-colors ${currentTab === 'exams' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
        >
          Exams
        </button>
      </nav>

      <div className="max-w-6xl mx-auto w-full">
        {currentTab === 'generate' && <GeneratePage />}
        {currentTab === 'publish' && <PublishPage />}
        {currentTab === 'rules' && <RuleBuilderPage />}
        {currentTab === 'students' && <StudentViewPage />}
        {currentTab === 'exams' && <ExamViews />}
      </div>
    </div>
  );
}

export default App;
