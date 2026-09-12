import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './components/layout/MainLayout';
import { GenerationProgressPage } from './pages/GenerationProgressPage';
import { ReviewTimetablePage } from './pages/ReviewTimetablePage';
import { GeneratePage } from './pages/GeneratePage';
import { StudentViewPage, FacultyViewPage } from './features/faculty-student-view';
import { CohortViewPage } from './pages/CohortViewPage';
import { ExamsModulePage } from './features/exam-module/ExamsModulePage';
import { PublishPage } from './features/publish/PublishPage';
import { RuleBuilderPage } from './features/rule-builder/RuleBuilderPage';
import { CoursesPage } from './pages/CoursesPage';
import { FacultyPage } from './pages/FacultyPage';
import { RoomsPage } from './pages/RoomsPage';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { SetupWizardPage } from './pages/SetupWizardPage';
import { SubstitutionsPage } from './pages/SubstitutionsPage';
import { ReportsPage } from './pages/ReportsPage';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="setup" element={<SetupWizardPage />} />
          <Route path="courses" element={<CoursesPage />} />
          <Route path="faculty" element={<FacultyPage />} />
          <Route path="rooms" element={<RoomsPage />} />
          
          <Route path="rules" element={<RuleBuilderPage />} />
          <Route path="generate" element={<GeneratePage />} />
          <Route path="progress" element={<GenerationProgressPage />} />
          <Route path="review" element={<ReviewTimetablePage />} />
          <Route path="publish" element={<PublishPage />} />
          
          <Route path="timetable" element={<CohortViewPage />} />
          <Route path="exams" element={<ExamsModulePage />} />
          <Route path="substitutions" element={<SubstitutionsPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="student-view" element={<StudentViewPage />} />
          
          {/* Legacy Faculty View accessible directly for now */}
          <Route path="faculty-view" element={<FacultyViewPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
