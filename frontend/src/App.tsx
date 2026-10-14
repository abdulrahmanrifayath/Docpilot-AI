import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProjectProvider } from './context/ProjectContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { ProjectDetailsPage } from './pages/ProjectDetailsPage';
import { DocumentationPage } from './pages/DocumentationPage';
import { DiagramsPage } from './pages/DiagramsPage';
import { AIChatPage } from './pages/AIChatPage';
import { OnboardingPage } from './pages/OnboardingPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ProjectProvider>
          <Routes>
            {/* Public Authentication & Landing Pages */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/landing" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected Application Routes (Protected via JWT & AuthContext) */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Layout>
                    <DashboardPage />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/projects"
              element={
                <ProtectedRoute>
                  <Layout>
                    <ProjectsPage />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/projects/:id"
              element={
                <ProtectedRoute>
                  <Layout>
                    <ProjectDetailsPage />
                  </Layout>
                </ProtectedRoute>
              }
            />
            {/* Legacy route alias */}
            <Route
              path="/repository/:id"
              element={
                <ProtectedRoute>
                  <Layout>
                    <ProjectDetailsPage />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/documentation"
              element={
                <ProtectedRoute>
                  <Layout>
                    <DocumentationPage />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/architecture"
              element={
                <ProtectedRoute>
                  <Layout>
                    <DiagramsPage />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/diagrams"
              element={
                <ProtectedRoute>
                  <Layout>
                    <DiagramsPage />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/sequences"
              element={
                <ProtectedRoute>
                  <Layout>
                    <DiagramsPage defaultTab="SEQUENCE_DIAGRAM" />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/chat"
              element={
                <ProtectedRoute>
                  <Layout>
                    <AIChatPage />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/onboarding"
              element={
                <ProtectedRoute>
                  <Layout>
                    <OnboardingPage />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <Layout>
                    <SettingsPage />
                  </Layout>
                </ProtectedRoute>
              }
            />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ProjectProvider>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
