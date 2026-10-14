import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ProjectProvider } from './context/ProjectContext';
import { Layout } from './components/Layout';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { ProjectDetailsPage } from './pages/ProjectDetailsPage';
import { DocumentationPage } from './pages/DocumentationPage';
import { DiagramsPage } from './pages/DiagramsPage';
import { AIChatPage } from './pages/AIChatPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <ProjectProvider>
        <Routes>
          {/* Public Landing Page */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/landing" element={<LandingPage />} />

          {/* Main Application with Developer Tool Layout (Sidebar + Top Bar) */}
          <Route
            path="/dashboard"
            element={
              <Layout>
                <DashboardPage />
              </Layout>
            }
          />
          <Route
            path="/projects"
            element={
              <Layout>
                <ProjectsPage />
              </Layout>
            }
          />
          <Route
            path="/projects/:id"
            element={
              <Layout>
                <ProjectDetailsPage />
              </Layout>
            }
          />
          {/* Legacy route alias */}
          <Route
            path="/repository/:id"
            element={
              <Layout>
                <ProjectDetailsPage />
              </Layout>
            }
          />
          <Route
            path="/documentation"
            element={
              <Layout>
                <DocumentationPage />
              </Layout>
            }
          />
          <Route
            path="/architecture"
            element={
              <Layout>
                <DiagramsPage />
              </Layout>
            }
          />
          <Route
            path="/diagrams"
            element={
              <Layout>
                <DiagramsPage />
              </Layout>
            }
          />
          <Route
            path="/sequences"
            element={
              <Layout>
                <DiagramsPage defaultTab="SEQUENCE_DIAGRAM" />
              </Layout>
            }
          />
          <Route
            path="/chat"
            element={
              <Layout>
                <AIChatPage />
              </Layout>
            }
          />
          <Route
            path="/settings"
            element={
              <Layout>
                <SettingsPage />
              </Layout>
            }
          />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </ProjectProvider>
    </BrowserRouter>
  );
};

export default App;
