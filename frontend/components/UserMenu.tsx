'use client';

import { useState, useRef, useEffect } from 'react';
import { LogOut, ChevronDown, LogIn } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

export default function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  if (!user) {
    return (
      <a
        id="user-menu-login"
        href="/auth/login"
        className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-600 transition-all duration-200 shadow-sm"
        style={{
          background: 'linear-gradient(135deg, var(--accent), var(--accent-bright))',
          color: '#fff',
        }}
      >
        <LogIn size={13} />
        Sign in
      </a>
    );
  }

  const initials = user.username.slice(0, 2).toUpperCase();

  return (
    <div ref={ref} className="relative">
      <button
        id="user-menu-trigger"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-lg px-2 py-1.5 transition-all duration-200"
        style={{
          background: open ? 'rgba(255,255,255,0.05)' : 'transparent',
          border: '1px solid transparent',
        }}
      >
        {user.avatar_url ? (
          <img
            src={user.avatar_url}
            alt={user.username}
            className="w-7 h-7 rounded-lg object-cover"
          />
        ) : (
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-700"
            style={{
              background: 'linear-gradient(135deg, var(--accent), var(--accent-bright))',
              color: '#fff',
            }}
          >
            {initials}
          </div>
        )}
        <span
          className="text-xs font-500 hidden sm:block max-w-[90px] truncate"
          style={{ color: 'var(--text-secondary)' }}
        >
          {user.username}
        </span>
        <ChevronDown
          size={12}
          className="transition-transform duration-200"
          style={{
            color: 'var(--text-muted)',
            transform: open ? 'rotate(180deg)' : 'none',
          }}
        />
      </button>

      {open && (
        <div
          className="absolute right-0 top-full mt-2 w-52 rounded-lg overflow-hidden animate-scale-in z-50"
          style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-strong)',
            boxShadow: '0 12px 40px rgba(0,0,0,0.4)',
          }}
        >
          {/* User info */}
          <div className="px-3.5 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
            <p className="text-xs font-600 truncate" style={{ color: 'var(--text-primary)' }}>
              {user.username}
            </p>
            <p className="text-[10px] truncate mt-0.5" style={{ color: 'var(--text-muted)' }}>
              {user.email}
            </p>
            {!user.is_verified && (
              <p className="text-[10px] mt-1 px-1.5 py-0.5 rounded inline-block"
                 style={{ background: 'rgba(245,158,11,0.1)', color: 'var(--accent-warm)' }}>
                ⚠ Email not verified
              </p>
            )}
          </div>

          {/* Actions */}
          <div className="py-1">
            <button
              id="user-menu-logout"
              onClick={async () => {
                setOpen(false);
                await logout();
                window.location.href = '/auth/login';
              }}
              className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-xs transition-colors"
              style={{ color: 'var(--error)' }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(248,113,113,0.06)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <LogOut size={14} />
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
