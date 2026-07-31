'use client';

import { useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { setAccessToken } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

function OAuthCallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refresh } = useAuth();

  useEffect(() => {
    const token = searchParams.get('access_token');
    if (token) {
      setAccessToken(token);
      // Refresh to load the user profile, then redirect
      refresh().then(() => {
        router.replace('/');
      });
    } else {
      router.replace('/auth/login');
    }
  }, [searchParams, refresh, router]);

  return (
    <div className="auth-card animate-fade-in">
      <div className="text-center">
        <span className="auth-spinner mb-4 mx-auto" style={{ width: 32, height: 32 }} />
        <h2 className="auth-title">Completing sign in…</h2>
        <p className="auth-subtitle">Please wait while we set up your session.</p>
      </div>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="auth-card animate-fade-in">
        <div className="text-center"><span className="auth-spinner" /></div>
      </div>
    }>
      <OAuthCallbackInner />
    </Suspense>
  );
}
