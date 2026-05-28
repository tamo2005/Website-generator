'use client';

import { Cpu, Globe, Clock } from 'lucide-react';

/* ────────────────────────────────────────────────────────────
   Props
──────────────────────────────────────────────────────────── */
interface StatusBarProps {
  isGenerating: boolean;
  tokenCount: number;
  totalTime: number | null;
  error: string | null;
  hasCode: boolean;
}

/* ────────────────────────────────────────────────────────────
   Component
──────────────────────────────────────────────────────────── */
export default function StatusBar({
  isGenerating,
  tokenCount,
  totalTime,
  error,
  hasCode,
}: StatusBarProps) {
  /* derive connection/status */
  let dotClass = '';
  let statusText = 'Ready';

  if (error) {
    dotClass = 'error';
    statusText = 'Error';
  } else if (isGenerating) {
    dotClass = 'loading';
    statusText = 'Generating…';
  } else if (hasCode) {
    dotClass = 'online';
    statusText = 'Complete';
  } else {
    dotClass = '';
    statusText = 'Idle';
  }

  return (
    <div
      className="flex-none flex items-center justify-between px-4 h-8 text-[10px]"
      style={{
        borderTop: '1px solid var(--border)',
        background: 'rgba(0,0,0,0.3)',
        color: 'var(--text-muted)',
      }}
    >
      {/* Left: status */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <div className={`status-dot ${dotClass}`} />
          <span>{statusText}</span>
        </div>

        {isGenerating && (
          <div className="flex items-center gap-1 animate-fade-in">
            <div
              className="h-1 rounded-full overflow-hidden"
              style={{ width: 60, background: 'rgba(255,255,255,0.06)' }}
            >
              <div
                className="h-full rounded-full animate-gradient"
                style={{
                  width: '40%',
                  background: 'linear-gradient(90deg,#6366f1,#a855f7,#6366f1)',
                  backgroundSize: '200% 100%',
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Center: model info */}
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1">
          <Cpu size={9} />
          Mistral-7B-Instruct
        </span>
        <span className="flex items-center gap-1">
          <Globe size={9} />
          HuggingFace Inference API
        </span>
      </div>

      {/* Right: stats */}
      <div className="flex items-center gap-3">
        {tokenCount > 0 && (
          <span className="mono">{tokenCount} tokens</span>
        )}
        {totalTime != null && (
          <span className="flex items-center gap-1 mono">
            <Clock size={9} />
            {(totalTime / 1000).toFixed(2)}s
          </span>
        )}
        <span className="opacity-40">AI Website Generator v1.0</span>
      </div>
    </div>
  );
}
