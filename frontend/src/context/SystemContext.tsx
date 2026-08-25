import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { SystemStatus } from '../types';
import { systemApi } from '../api/system';

interface SystemContextType {
  status: SystemStatus | null;
  isLoading: boolean;
  error: string | null;
  refreshStatus: () => Promise<void>;
}

const SystemContext = createContext<SystemContextType | undefined>(undefined);

export const SystemProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refreshStatus = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await systemApi.getStatus();
      setStatus(data);
    } catch (err: any) {
      console.error('Failed to fetch system status:', err);
      setError(err.message || 'Unable to connect to DocPilot backend service.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshStatus();
    // Poll every 30 seconds
    const interval = setInterval(refreshStatus, 30000);
    return () => clearInterval(interval);
  }, [refreshStatus]);

  return (
    <SystemContext.Provider value={{ status, isLoading, error, refreshStatus }}>
      {children}
    </SystemContext.Provider>
  );
};

export const useSystem = (): SystemContextType => {
  const context = useContext(SystemContext);
  if (!context) {
    throw new Error('useSystem must be used within a SystemProvider');
  }
  return context;
};
