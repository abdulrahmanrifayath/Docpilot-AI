import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { SystemProvider } from './context/SystemContext';
import { ProjectProvider } from './context/ProjectContext';
import { AppLayout } from './components/layout/AppLayout';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { ProjectDetailsPage } from './pages/ProjectDetailsPage';
import { DocumentationPage } from './pages/DocumentationPage';
import { DiagramsPage } from './pages/DiagramsPage';
import { AIChatPage } from './pages/AIChatPage';
import { SettingsPage } from './pages/SettingsPage';
import { NotFoundPage } from './pages/NotFoundPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <SystemProvider>
        <ProjectProvider>
          <Routes>
            {/* Public Landing Page */}
            <Route path="/" element={<LandingPage />} />

            {/* App Layout for Main Developer Tool Views */}
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/projects" element={<ProjectsPage />} />
              <Route path="/projects/:id" element={<ProjectDetailsPage />} />
              <Route path="/projects/:id/docs" element={<DocumentationPage />} />
              <Route path="/documentation" element={<DocumentationPage />} />
              <Route path="/projects/:id/diagrams" element={<DiagramsPage />} />
              <Route path="/diagrams" element={<DiagramsPage />} />
              <Route path="/projects/:id/chat" element={<AIChatPage />} />
              <Route path="/chat" element={<AIChatPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </ProjectProvider>
      </SystemProvider>
    </BrowserRouter>
  );
};

export default App;
