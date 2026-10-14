import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, AuthResponse } from '../types';
import {
  getAuthToken,
  setAuthToken,
  loginUser,
  registerUser,
  fetchCurrentUser,
  logoutUser,
} from '../api/client';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<AuthResponse>;
  register: (email: string, password: string, fullName?: string) => Promise<AuthResponse>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(getAuthToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const initAuth = async () => {
    const existingToken = getAuthToken();
    if (!existingToken) {
      setUser(null);
      setToken(null);
      setIsLoading(false);
      return;
    }

    try {
      const currentUser = await fetchCurrentUser();
      setUser(currentUser);
      setToken(existingToken);
    } catch {
      // Stored token is invalid or expired
      setUser(null);
      setToken(null);
      setAuthToken(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    initAuth();
  }, []);

  const login = async (email: string, password: string): Promise<AuthResponse> => {
    const authData = await loginUser({ email, password });
    setToken(authData.access_token);
    setUser(authData.user);
    return authData;
  };

  const register = async (
    email: string,
    password: string,
    fullName?: string
  ): Promise<AuthResponse> => {
    const authData = await registerUser({
      email,
      password,
      full_name: fullName,
    });
    setToken(authData.access_token);
    setUser(authData.user);
    return authData;
  };

  const logout = () => {
    logoutUser();
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    if (!getAuthToken()) return;
    try {
      const u = await fetchCurrentUser();
      setUser(u);
    } catch {
      logout();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
