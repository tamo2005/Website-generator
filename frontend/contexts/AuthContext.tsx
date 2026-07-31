'use client';

/**
 * contexts/AuthContext.tsx — Global authentication state
 *
 * Access token stored in React state (memory) — never localStorage.
 * Refresh token lives in HttpOnly cookie — managed by the backend.
 *
 * On mount:  tries silent refresh via cookie → loads user if token exists.
 * On login:  stores access token in memory → fetches user profile.
 * On logout: clears memory token → calls backend to revoke + clear cookie.
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from 'react';
import { authAPI, setAccessToken, type UserProfile } from '@/lib/api';

/* ────────────────────────────────────────────────────────── */

interface AuthContextType {
  user: UserProfile | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<boolean>;
  updateUser: (data: Partial<UserProfile>) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

/* ────────────────────────────────────────────────────────── */

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Silent refresh on mount — if cookie exists, get a new access token
  useEffect(() => {
    (async () => {
      try {
        const tokens = await authAPI.refresh();
        if (tokens) {
          const profile = await authAPI.getMe();
          setUser(profile);
        }
      } catch {
        // No valid session — that's fine
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    await authAPI.login(email, password);
    const profile = await authAPI.getMe();
    setUser(profile);
  }, []);

  const logout = useCallback(async () => {
    await authAPI.logout();
    setUser(null);
  }, []);

  const refresh = useCallback(async (): Promise<boolean> => {
    const tokens = await authAPI.refresh();
    if (tokens) {
      try {
        const profile = await authAPI.getMe();
        setUser(profile);
        return true;
      } catch {
        return false;
      }
    }
    return false;
  }, []);

  const updateUser = useCallback((data: Partial<UserProfile>) => {
    setUser((prev) => (prev ? { ...prev, ...data } : prev));
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refresh,
        updateUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/* ────────────────────────────────────────────────────────── */

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
