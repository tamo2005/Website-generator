'use client';

import { useState, useRef, useCallback } from 'react';

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
      const res = await fetch(`${API_URL}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt.trim() }),
        signal: controller.signal,
      });

      if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
          const json = await res.json();
          detail = json.detail || detail;
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
      const msg = err instanceof Error ? err.message : 'Unexpected error';
      setState((prev) => ({
        ...prev,
        isGenerating: false,
        error: `Generation failed — ${msg}. Check your OpenRouter key and retry.`,
      }));
    }
  }, []);

  return { ...state, generate, cancel, reset };
}
