import React from 'react';
import { ProjectDetailsPage } from './ProjectDetailsPage';

interface RepositoryDetailPageProps {
  onOpenChat?: (repoId: string, repoName: string) => void;
}

export const RepositoryDetailPage: React.FC<RepositoryDetailPageProps> = () => {
  return <ProjectDetailsPage />;
};

export default RepositoryDetailPage;
