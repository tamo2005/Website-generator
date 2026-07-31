'use client';

import { AuthProvider } from '@/contexts/AuthContext';
import { type ReactNode } from 'react';

/**
 * Client-side providers wrapper.
 * 
 * layout.tsx is a server component (it exports metadata), so we need
 * a separate client component to wrap children with context providers.
 */
export function Providers({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
