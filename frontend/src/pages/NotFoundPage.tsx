import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/common/Button';
import { ArrowLeft, FileQuestion } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center p-6">
      <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4 shadow-glow">
        <FileQuestion className="w-8 h-8" />
      </div>
      <h1 className="text-2xl font-bold text-white tracking-tight">404 - Page Not Found</h1>
      <p className="text-xs text-slate-400 mt-2 max-w-sm">
        The requested route or documentation view does not exist in this DocPilot AI workspace.
      </p>
      <Link to="/dashboard" className="mt-6">
        <Button variant="primary" size="md" leftIcon={<ArrowLeft className="w-4 h-4" />}>
          Back to Dashboard
        </Button>
      </Link>
    </div>
  );
};
