import React, { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { RepositoryDetailPage } from './pages/RepositoryDetailPage';
import { SettingsPage } from './pages/SettingsPage';
import { ChatDrawer } from './components/ChatDrawer';

export const App: React.FC = () => {
  const [isChatOpen, setIsChatOpen] = useState<boolean>(false);
  const [activeRepoId, setActiveRepoId] = useState<string | undefined>(undefined);
  const [activeRepoName, setActiveRepoName] = useState<string | undefined>(undefined);

  const handleOpenChat = (repoId: string, repoName: string) => {
    setActiveRepoId(repoId);
    setActiveRepoName(repoName);
    setIsChatOpen(true);
  };

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col">
        <Navbar
          onToggleChat={() => setIsChatOpen(!isChatOpen)}
          isChatOpen={isChatOpen}
        />

        <main className="flex-1">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route
              path="/repository/:id"
              element={<RepositoryDetailPage onOpenChat={handleOpenChat} />}
            />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>

        <ChatDrawer
          isOpen={isChatOpen}
          onClose={() => setIsChatOpen(false)}
          repositoryId={activeRepoId}
          repositoryName={activeRepoName}
        />
      </div>
    </BrowserRouter>
  );
};

export default App;
