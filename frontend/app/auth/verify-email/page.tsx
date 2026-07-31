'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { authAPI, APIError } from '@/lib/api';

function VerifyEmailInner() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');

  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('Missing verification token.');
      return;
    }

    (async () => {
      try {
        await authAPI.verifyEmail(token);
        setStatus('success');
        setMessage('Your email has been verified!');
      } catch (err) {
        setStatus('error');
        setMessage(
          err instanceof APIError ? err.message : 'Verification failed.',
        );
      }
    })();
  }, [token]);

  return (
    <div className="auth-card animate-fade-in">
      <div className="text-center">
        {status === 'loading' && (
          <>
            <span className="auth-spinner mb-4 mx-auto" style={{ width: 32, height: 32 }} />
            <h2 className="auth-title">Verifying your email…</h2>
          </>
        )}
        {status === 'success' && (
          <>
            <div className="text-4xl mb-4">🎉</div>
            <h2 className="auth-title">Email verified!</h2>
            <p className="auth-subtitle">{message}</p>
            <Link href="/auth/login" className="auth-link mt-6 inline-block">
              Sign in →
            </Link>
          </>
        )}
        {status === 'error' && (
          <>
            <div className="text-4xl mb-4">❌</div>
            <h2 className="auth-title">Verification failed</h2>
            <p className="auth-subtitle">{message}</p>
            <Link href="/auth/login" className="auth-link mt-6 inline-block">
              ← Back to Login
            </Link>
          </>
        )}
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <div className="auth-card animate-fade-in">
        <div className="text-center"><span className="auth-spinner" /></div>
      </div>
    }>
      <VerifyEmailInner />
    </Suspense>
  );
}
