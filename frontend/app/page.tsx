'use client';

import { useCallback, useState } from 'react';
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
        <div
          style={{
            position: 'absolute',
            inset: '8% 6%',
            border: '1px solid rgba(255,255,255,0.04)',
            borderRadius: '32px',
            background:
              'linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.005))',
          }}
        />
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backgroundImage:
              'linear-gradient(rgba(255,255,255,0.045) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.045) 1px, transparent 1px)',
            backgroundSize: '72px 72px',
            maskImage: 'linear-gradient(180deg, rgba(0,0,0,0.55), transparent 82%)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            top: '-18%',
            left: '-8%',
            width: '52vw',
            height: '52vw',
            borderRadius: '50%',
            background:
              'radial-gradient(circle, rgba(34,211,238,0.12) 0%, transparent 68%)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            bottom: '-22%',
            right: '-8%',
            width: '48vw',
            height: '48vw',
            borderRadius: '50%',
            background:
              'radial-gradient(circle, rgba(244,63,94,0.1) 0%, transparent 70%)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            inset: '12% 18% auto auto',
            width: 240,
            height: 240,
            borderRadius: '50%',
            border: '1px solid rgba(34,211,238,0.16)',
            filter: 'blur(0.4px)',
          }}
        />
      </div>

      {/* ── Main workspace ──────────────────────────────────── */}
      <main
        className="flex flex-1 overflow-hidden"
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
function usePromptState(initial: string): [string, (v: string) => void] {
  const [value, setValue] = useState(initial);
  return [value, setValue];
}
