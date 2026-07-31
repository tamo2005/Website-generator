'use client';

import { useState, useRef, useCallback } from 'react';
import { getAccessToken } from '@/lib/api';

/* ────────────────────────────────────────────────────────────
   Types
──────────────────────────────────────────────────────────── */
export interface StreamingStats {
  ttft: number | null;          // time-to-first-token (ms)
  tokensPerSec: number | null;
  totalTime: number | null;
  tokenCount: number;
}

export interface StreamingState extends StreamingStats {
  streamedCode: string;
  isGenerating: boolean;
  error: string | null;
}

export interface UseStreamingGenerationReturn extends StreamingState {
  generate: (prompt: string) => Promise<void>;
  cancel: () => void;
  reset: () => void;
}

/* ────────────────────────────────────────────────────────────
   Constants
──────────────────────────────────────────────────────────── */
const API_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const INITIAL_STATE: StreamingState = {
  streamedCode: '',
  isGenerating: false,
  error: null,
  ttft: null,
  tokensPerSec: null,
  totalTime: null,
  tokenCount: 0,
};

/* ────────────────────────────────────────────────────────────
   Hook
──────────────────────────────────────────────────────────── */
export function useStreamingGeneration(): UseStreamingGenerationReturn {
  const [state, setState] = useState<StreamingState>(INITIAL_STATE);
  const abortRef = useRef<AbortController | null>(null);

  /* ── cancel ─────────────────────────────────────────────── */
  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setState((prev) => ({ ...prev, isGenerating: false }));
  }, []);

  /* ── reset ──────────────────────────────────────────────── */
  const reset = useCallback(() => {
    setState(INITIAL_STATE);
  }, []);

  /* ── generate ───────────────────────────────────────────── */
  const generate = useCallback(async (prompt: string) => {
    // Abort any in-flight request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const startTime = performance.now();
    let firstTokenAt: number | null = null;
    let tokenCount = 0;

    setState({
      ...INITIAL_STATE,
      isGenerating: true,
    });

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      const token = getAccessToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch(`${API_URL}/api/v1/generate`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ prompt: prompt.trim() }),
        signal: controller.signal,
        credentials: 'include',
      });

      if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
          const json = await res.json();
          detail = json.error?.message || json.detail || json.message || detail;
        } catch {}
        throw new Error(detail);
      }

      if (!res.body) throw new Error('No response body from server.');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() ?? '';

        for (const evt of events) {
          // Handle error events
          if (evt.startsWith('event: error')) {
            const dataLine = evt.split('\n').find((l) => l.startsWith('data: '));
            const msg = dataLine?.replace(/^data:\s*/, '') ?? 'Unknown stream error';
            throw new Error(msg);
          }

          const dataLine = evt.split('\n').find((l) => l.startsWith('data: '));
          if (!dataLine) continue;

          const token = dataLine.replace(/^data:\s*/, '');
          if (token === '[DONE]') break;

          // Record TTFT on first real token
          if (!firstTokenAt) {
            firstTokenAt = performance.now() - startTime;
          }
          tokenCount++;

          // Decode escaped newlines from the SSE formatter
          const decoded = token.replace(/\\n/g, '\n');

          setState((prev) => ({
            ...prev,
            streamedCode: prev.streamedCode + decoded,
            ttft: firstTokenAt,
            tokenCount,
          }));
        }
      }

      const totalTime = performance.now() - startTime;
      setState((prev) => ({
        ...prev,
        isGenerating: false,
        totalTime,
        tokensPerSec: tokenCount > 0 ? tokenCount / (totalTime / 1000) : null,
      }));
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        setState((prev) => ({ ...prev, isGenerating: false }));
        return;
      }
      const rawMsg = err instanceof Error ? err.message : 'Unexpected error';
      let userMsg = rawMsg;

      if (
        rawMsg.includes('Failed to fetch') ||
        rawMsg.includes('NetworkError') ||
        rawMsg.includes('Load failed')
      ) {
        userMsg =
          'Could not connect to the backend server (http://localhost:8000). Please ensure the backend is running.';
      } else if (
        rawMsg.includes('Not authenticated') ||
        rawMsg.includes('HTTP 401') ||
        rawMsg.includes('AUTHENTICATION_REQUIRED')
      ) {
        userMsg = 'Authentication required. Please log in to generate websites.';
      } else if (
        rawMsg.includes('Email not verified') ||
        rawMsg.includes('HTTP 403') ||
        rawMsg.includes('EMAIL_NOT_VERIFIED')
      ) {
        userMsg = 'Email verification required. Please verify your account to generate websites.';
      } else if (rawMsg.includes('OPENROUTER_API_KEY')) {
        userMsg =
          'OpenRouter API key is missing or not configured. Please set OPENROUTER_API_KEY in backend/.env.';
      } else if (!userMsg.startsWith('Generation failed')) {
        userMsg = `Generation failed — ${rawMsg}. Check your OpenRouter key and retry.`;
      }

      setState((prev) => ({
        ...prev,
        isGenerating: false,
        error: userMsg,
      }));
    }
  }, []);

  return { ...state, generate, cancel, reset };
}
