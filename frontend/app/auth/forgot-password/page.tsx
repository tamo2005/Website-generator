'use client';

import { useState } from 'react';
import Link from 'next/link';
import { authAPI, APIError } from '@/lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await authAPI.forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(
        err instanceof APIError ? err.message : 'Something went wrong.',
      );
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <div className="auth-card animate-fade-in">
        <div className="text-center">
          <div className="text-4xl mb-4">📬</div>
          <h2 className="auth-title">Check your inbox</h2>
          <p className="auth-subtitle">
            If an account exists with <strong style={{ color: 'var(--text-primary)' }}>{email}</strong>,
            we&apos;ve sent a password reset link.
          </p>
          <Link href="/auth/login" className="auth-link mt-6 inline-block">
            ← Back to Login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-card animate-fade-in">
      <div className="text-center mb-8">
        <h2 className="auth-title">Forgot your password?</h2>
        <p className="auth-subtitle">Enter your email and we&apos;ll send a reset link</p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label className="auth-label" htmlFor="forgot-email">Email</label>
          <input
            id="forgot-email"
            type="email"
            className="auth-input"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
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
          {loading ? 'Sending…' : 'Send Reset Link'}
        </button>
      </form>

      <p className="text-center mt-6 text-xs" style={{ color: 'var(--text-muted)' }}>
        Remember your password?{' '}
        <Link href="/auth/login" className="auth-link">Sign in</Link>
      </p>
    </div>
  );
}
