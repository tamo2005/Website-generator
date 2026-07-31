'use client';

import { useCallback, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import PromptPanel from '@/components/PromptPanel';
import PreviewPane from '@/components/PreviewPane';
import StatusBar from '@/components/StatusBar';
import { useStreamingGeneration } from '@/hooks/useStreamingGeneration';
import { useAuth } from '@/contexts/AuthContext';

/* ────────────────────────────────────────────────────────────
   WorkspaceContainer — owns all global state
──────────────────────────────────────────────────────────── */
export default function Page() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace('/auth/login');
    }
  }, [isLoading, isAuthenticated, router]);

  const {
    streamedCode,
    isGenerating,
    error,
    ttft,
    tokensPerSec,
    totalTime,
    tokenCount,
    generate,
    cancel,
    reset,
  } = useStreamingGeneration();

  const [prompt, setPrompt] = usePromptState('');

  const handleGenerate = useCallback(() => {
    if (prompt.trim().length >= 3) generate(prompt);
  }, [prompt, generate]);

  const handlePromptChange = useCallback(
    (v: string) => {
      setPrompt(v);
      if (error) reset();
    },
    [setPrompt, error, reset],
  );

  // Auth loading state
  if (isLoading) {
    return (
      <div className="loading-screen">
        <div className="loading-orb" />
      </div>
    );
  }

  // Not authenticated — will redirect via useEffect
  if (!isAuthenticated) {
    return (
      <div className="loading-screen">
        <div className="loading-orb" />
      </div>
    );
  }

  return (
    <div
      className="flex flex-col"
      style={{ height: '100dvh', background: 'var(--bg-base)' }}
    >
      {/* ── Main workspace ──────────────────────────────────── */}
      <main
        className="flex flex-1 overflow-hidden animate-fade-in"
        style={{ position: 'relative', zIndex: 1 }}
      >
        {/* Sidebar / Prompt Panel */}
        <div style={{ width: 360, minWidth: 320, flexShrink: 0 }}>
          <PromptPanel
            prompt={prompt}
            onPromptChange={handlePromptChange}
            onGenerate={handleGenerate}
            onCancel={cancel}
            isGenerating={isGenerating}
            error={error}
            tokenCount={tokenCount}
            ttft={ttft}
            tokensPerSec={tokensPerSec}
            totalTime={totalTime}
          />
        </div>

        {/* Divider */}
        <div
          style={{
            width: 1,
            background: 'var(--border)',
            flexShrink: 0,
          }}
        />

        {/* Preview / Code area */}
        <div className="flex-1 overflow-hidden">
          <PreviewPane code={streamedCode} isGenerating={isGenerating} />
        </div>
      </main>

      {/* ── Status bar ──────────────────────────────────────── */}
      <StatusBar
        isGenerating={isGenerating}
        tokenCount={tokenCount}
        totalTime={totalTime}
        error={error}
        hasCode={streamedCode.length > 0}
      />
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Minimal hook to avoid prop drilling React.useState
──────────────────────────────────────────────────────────── */
function usePromptState(initial: string): [string, (v: string) => void] {
  const [value, setValue] = useState(initial);
  return [value, setValue];
}
