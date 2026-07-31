'use client';

/**
 * lib/api.ts — API client with auth token management
 *
 * Handles:
 * - Attaching the access token to requests
 * - Auto-refreshing expired tokens via the HttpOnly cookie
 * - Consistent error parsing from the standard response envelope
 */

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/* ──────────────────────────────────────────────────────────
   Token storage (in-memory only — NOT localStorage)
   XSS-safe: tokens never touch persistent browser storage
────────────────────────────────────────────────────────── */
let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

/* ──────────────────────────────────────────────────────────
   API error type
────────────────────────────────────────────────────────── */
export class APIError extends Error {
  code: string;
  status: number;
  requestId: string | null;

  constructor(message: string, code: string, status: number, requestId: string | null = null) {
    super(message);
    this.name = 'APIError';
    this.code = code;
    this.status = status;
    this.requestId = requestId;
  }
}

/* ──────────────────────────────────────────────────────────
   Core fetch wrapper
────────────────────────────────────────────────────────── */
interface FetchOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  skipAuth?: boolean;
}

async function apiFetch<T = unknown>(
  path: string,
  options: FetchOptions = {},
): Promise<T> {
  const { body, skipAuth = false, headers: extraHeaders, ...rest } = options;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((extraHeaders as Record<string, string>) || {}),
  };

  if (!skipAuth && accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...rest,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    credentials: 'include', // Always send HttpOnly cookies
  });

  // Try to parse the response body
  let json: any;
  try {
    json = await res.json();
  } catch {
    if (!res.ok) {
      throw new APIError(
        `HTTP ${res.status}`,
        'NETWORK_ERROR',
        res.status,
      );
    }
    return undefined as T;
  }

  // Handle error responses from the standard envelope
  if (!res.ok || json.success === false) {
    const errorData = json.error || {};
    throw new APIError(
      errorData.message || json.message || `HTTP ${res.status}`,
      errorData.code || 'UNKNOWN_ERROR',
      res.status,
      json.request_id || null,
    );
  }

  // Return the data field from the standard envelope
  return json.data !== undefined ? json.data : json;
}

/* ──────────────────────────────────────────────────────────
   Auth API calls
────────────────────────────────────────────────────────── */
export interface AuthTokens {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserProfile {
  id: string;
  email: string;
  username: string;
  role: string;
  avatar_url: string | null;
  bio: string | null;
  is_verified: boolean;
  created_at: string;
}

export const authAPI = {
  register: (email: string, username: string, password: string) =>
    apiFetch<UserProfile>('/api/v1/auth/register', {
      method: 'POST',
      body: { email, username, password },
      skipAuth: true,
    }),

  login: async (email: string, password: string): Promise<AuthTokens> => {
    const tokens = await apiFetch<AuthTokens>('/api/v1/auth/login', {
      method: 'POST',
      body: { email, password },
      skipAuth: true,
    });
    setAccessToken(tokens.access_token);
    return tokens;
  },

  refresh: async (): Promise<AuthTokens | null> => {
    try {
      const tokens = await apiFetch<AuthTokens>('/api/v1/auth/refresh', {
        method: 'POST',
        skipAuth: true,
      });
      setAccessToken(tokens.access_token);
      return tokens;
    } catch {
      setAccessToken(null);
      return null;
    }
  },

  logout: async (): Promise<void> => {
    try {
      await apiFetch('/api/v1/auth/logout', { method: 'POST' });
    } finally {
      setAccessToken(null);
    }
  },

  getMe: () => apiFetch<UserProfile>('/api/v1/auth/me'),

  updateMe: (data: { username?: string; avatar_url?: string; bio?: string }) =>
    apiFetch<UserProfile>('/api/v1/auth/me', {
      method: 'PATCH',
      body: data,
    }),

  verifyEmail: (token: string) =>
    apiFetch('/api/v1/auth/verify-email', {
      method: 'POST',
      body: { token },
      skipAuth: true,
    }),

  forgotPassword: (email: string) =>
    apiFetch('/api/v1/auth/forgot-password', {
      method: 'POST',
      body: { email },
      skipAuth: true,
    }),

  resetPassword: (token: string, new_password: string) =>
    apiFetch('/api/v1/auth/reset-password', {
      method: 'POST',
      body: { token, new_password },
      skipAuth: true,
    }),

  getGoogleOAuthURL: () => `${API_URL}/api/v1/auth/oauth/google`,
  getGitHubOAuthURL: () => `${API_URL}/api/v1/auth/oauth/github`,
};
