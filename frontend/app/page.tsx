'use client';

import { useCallback } from 'react';
import PromptPanel from '@/components/PromptPanel';
import PreviewPane from '@/components/PreviewPane';
import StatusBar from '@/components/StatusBar';
import { useStreamingGeneration } from '@/hooks/useStreamingGeneration';

/* ────────────────────────────────────────────────────────────
   WorkspaceContainer — owns all global state
──────────────────────────────────────────────────────────── */
export default function Page() {
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

  // We keep prompt state local (not in the hook) so the textarea
  // stays responsive even during streaming.
  const [prompt, setPrompt] = usePromptState('');

  const handleGenerate = useCallback(() => {
    if (prompt.trim().length >= 3) generate(prompt);
  }, [prompt, generate]);

  const handlePromptChange = useCallback(
    (v: string) => {
      setPrompt(v);
      // If there was an error and the user starts typing, clear it
      if (error) reset();
    },
    [setPrompt, error, reset],
  );

  return (
    <div
      className="flex flex-col"
      style={{ height: '100dvh', background: 'var(--bg-base)' }}
    >
      {/* ── Decorative background ───────────────────────────── */}
      <div
        aria-hidden="true"
        style={{
          position: 'fixed',
          inset: 0,
          pointerEvents: 'none',
          zIndex: 0,
          overflow: 'hidden',
        }}
      >
        {/* Orb 1 */}
        <div
          style={{
            position: 'absolute',
            top: '-20%',
            left: '-10%',
            width: '60vw',
            height: '60vw',
            borderRadius: '50%',
            background:
              'radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%)',
          }}
        />
        {/* Orb 2 */}
        <div
          style={{
            position: 'absolute',
            bottom: '-20%',
            right: '-10%',
            width: '50vw',
            height: '50vw',
            borderRadius: '50%',
            background:
              'radial-gradient(circle, rgba(168,85,247,0.07) 0%, transparent 70%)',
          }}
        />
      </div>

      {/* ── Main workspace ──────────────────────────────────── */}
      <main
        className="flex flex-1 overflow-hidden"
        style={{ position: 'relative', zIndex: 1 }}
      >
        {/* Sidebar / Prompt Panel */}
        <div style={{ width: 340, minWidth: 300, flexShrink: 0 }}>
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

        {/* Resizable divider visual */}
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
import { useState } from 'react';

function usePromptState(initial: string): [string, (v: string) => void] {
  const [value, setValue] = useState(initial);
  return [value, setValue];
}
