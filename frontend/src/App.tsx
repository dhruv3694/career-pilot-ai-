import React from 'react';
import { Route, Routes } from 'react-router-dom';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { Dashboard } from './pages/Dashboard';
import { ResumeStudio } from './pages/ResumeStudio';
import { ATSValidation } from './pages/ATSValidation';
import { JobExplorer } from './pages/JobExplorer';
import { JobMatchComparison } from './pages/JobMatchComparison';
import { CareerRoadmap } from './pages/CareerRoadmap';
import { InterviewLab } from './pages/InterviewLab';
import { CareerFairsEvents } from './pages/CareerFairsEvents';
import { AgentControlCenter } from './pages/AgentControlCenter';
import { MemoryPrivacy } from './pages/MemoryPrivacy';
import { ApprovalsSettings } from './pages/ApprovalsSettings';
import { Demonstrations } from './pages/Demonstrations';

const App: React.FC = () => (
  <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
    <Navbar />
    <div className="flex min-h-0 flex-1">
      <Sidebar />
      <main className="min-w-0 flex-1">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/resume-studio" element={<ResumeStudio />} />
          <Route path="/ats-validation" element={<ATSValidation />} />
          <Route path="/jobs" element={<JobExplorer />} />
          <Route path="/matching" element={<JobMatchComparison />} />
          <Route path="/roadmap" element={<CareerRoadmap />} />
          <Route path="/interview" element={<InterviewLab />} />
          <Route path="/events" element={<CareerFairsEvents />} />
          <Route path="/agents" element={<AgentControlCenter />} />
          <Route path="/memory" element={<MemoryPrivacy />} />
          <Route path="/settings" element={<ApprovalsSettings />} />
          <Route path="/demonstrations" element={<Demonstrations />} />
        </Routes>
      </main>
    </div>
  </div>
);

export default App;
