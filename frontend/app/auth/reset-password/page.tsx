'use client';

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { authAPI, APIError } from '@/lib/api';

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token') || '';

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }

    if (!token) {
      setError('Missing reset token. Please use the link from your email.');
      return;
    }

    setLoading(true);
    try {
      await authAPI.resetPassword(token, password);
      setSuccess(true);
    } catch (err) {
      setError(
        err instanceof APIError ? err.message : 'Reset failed. Please try again.',
      );
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="auth-card animate-fade-in">
        <div className="text-center">
          <div className="text-4xl mb-4">✅</div>
          <h2 className="auth-title">Password reset!</h2>
          <p className="auth-subtitle">
            Your password has been changed. You can now log in with your new password.
          </p>
          <Link href="/auth/login" className="auth-link mt-6 inline-block">
            Go to Login →
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-card animate-fade-in">
      <div className="text-center mb-8">
        <h2 className="auth-title">Reset your password</h2>
        <p className="auth-subtitle">Choose a new password for your account</p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label className="auth-label" htmlFor="reset-password">New Password</label>
          <input
            id="reset-password"
            type="password"
            className="auth-input"
            placeholder="Min 8 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
          />
        </div>
        <div>
          <label className="auth-label" htmlFor="reset-confirm">Confirm Password</label>
          <input
            id="reset-confirm"
            type="password"
            className="auth-input"
            placeholder="Re-enter password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
          />
        </div>

        {error && (
          <div className="auth-error animate-fade-in">⚠️ {error}</div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="btn-generate w-full py-3 flex items-center justify-center gap-2 mt-2"
        >
          {loading ? <span className="auth-spinner" /> : null}
          {loading ? 'Resetting…' : 'Reset Password'}
        </button>
      </form>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={
      <div className="auth-card animate-fade-in">
        <div className="text-center"><span className="auth-spinner" /></div>
      </div>
    }>
      <ResetPasswordForm />
    </Suspense>
  );
}
