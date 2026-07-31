'use client';

import { Sparkles, Zap, Square, ChevronRight } from 'lucide-react';
import UserMenu from './UserMenu';

/* ────────────────────────────────────────────────────────────
   Preset definitions
──────────────────────────────────────────────────────────── */
const PRESETS = [
  {
    icon: '🚀',
    label: 'SaaS Landing',
    prompt:
      'Build a modern SaaS landing page for a note-taking app called "Notara". Include: a hero section with large gradient headline and subtitle, a features section with 6 icon cards (collaboration, AI-powered, offline-ready, cross-platform, version history, encryption), a 3-tier pricing table (Free / Pro / Team), customer testimonials with avatars, and a CTA footer. Use a deep indigo/purple color scheme with a dark background.',
  },
  {
    icon: '💼',
    label: 'Portfolio',
    prompt:
      'Create a personal portfolio for a full-stack developer named "Alex Chen". Include: a hero section with animated typewriter greeting, skills grid (React, Node, Python, Postgres, Docker, AWS), 4 project cards with descriptions and tech stack badges, a timeline of work experience, and a contact section. Dark theme with electric cyan and violet accents.',
  },
  {
    icon: '🛒',
    label: 'E-commerce',
    prompt:
      'Design a premium e-commerce product page for "AuraPods" wireless headphones priced at $299. Show: a hero with a large product image placeholder, color selector dots, star ratings (4.8/5 with 2.4k reviews), an add-to-cart button, product specifications table, collapsible FAQ accordion, and a related products grid. Clean white/cream theme with black accents.',
  },
  {
    icon: '📝',
    label: 'Blog',
    prompt:
      'Build a modern editorial blog homepage for a publication called "The Gradient". Include: a featured article hero with category badge, author avatar and date, a 3-column article card grid with reading time estimates, a sticky sidebar with trending posts and newsletter signup, and a category filter bar. Warm amber and cream color palette.',
  },
  {
    icon: '📊',
    label: 'Dashboard',
    prompt:
      'Create an analytics dashboard UI. Include: a collapsible left sidebar nav with icons (Home, Analytics, Reports, Users, Settings), a top header with search bar and user avatar, 4 KPI metric cards (Revenue, Users, Conversion, Churn) with trend arrows, a line chart placeholder, a recent-transactions table, and a right panel with activity feed. Dark theme with purple and emerald accents.',
  },
  {
    icon: '🎨',
    label: 'Agency',
    prompt:
      'Design a creative digital agency homepage called "Parallax Studio". Include: a bold full-viewport hero with large display typography and a "View our work" CTA, an animated work portfolio grid (6 items with overlay captions on hover), a services section with 4 cards, team member profile cards, and client logo strip. Monochrome with bold accent colors.',
  },
];

/* ────────────────────────────────────────────────────────────
   Props
──────────────────────────────────────────────────────────── */
interface PromptPanelProps {
  prompt: string;
  onPromptChange: (v: string) => void;
  onGenerate: () => void;
  onCancel: () => void;
  isGenerating: boolean;
  error: string | null;
  tokenCount: number;
  ttft: number | null;
  tokensPerSec: number | null;
  totalTime: number | null;
  maxChars?: number;
}

/* ────────────────────────────────────────────────────────────
   Component
──────────────────────────────────────────────────────────── */
export default function PromptPanel({
  prompt,
  onPromptChange,
  onGenerate,
  onCancel,
  isGenerating,
  error,
  tokenCount,
  ttft,
  tokensPerSec,
  totalTime,
  maxChars = 8000,
}: PromptPanelProps) {
  const charCount = prompt.length;
  const charPct = Math.min(charCount / maxChars, 1);
  const canGenerate = prompt.trim().length >= 3 && !isGenerating;

  return (
    <aside
      className="flex flex-col h-full overflow-hidden animate-slide-in-left"
      style={{
        borderRight: '1px solid var(--border)',
        background: 'linear-gradient(180deg, var(--bg-surface), var(--bg-base))',
      }}
    >
      {/* ── Header ─────────────────────────────────────────── */}
      <div
        className="flex-none px-5 py-4"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center animate-float"
              style={{
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                boxShadow: '0 4px 16px rgba(99,102,241,0.25)',
              }}
            >
              <Sparkles size={14} className="text-white" />
            </div>
            <div>
              <h1 className="text-sm font-700 tracking-tight" style={{ color: 'var(--text-primary)' }}>
                Site Generator
              </h1>
              <p className="text-[10px] tracking-wide" style={{ color: 'var(--text-muted)' }}>
                Powered by AI
              </p>
            </div>
          </div>
          <UserMenu />
        </div>
      </div>

      {/* ── Scroll area ────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-4">

        {/* Prompt label */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-600 tracking-wide" style={{ color: 'var(--text-secondary)' }}>
              Describe your website
            </label>
            <span
              className="text-[10px] mono"
              style={{ color: charPct > 0.9 ? 'var(--error)' : 'var(--text-muted)' }}
            >
              {charCount}/{maxChars}
            </span>
          </div>

          {/* Progress bar */}
          <div
            className="w-full h-[2px] rounded-full mb-2 overflow-hidden"
            style={{ background: 'var(--border)' }}
          >
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${charPct * 100}%`,
                background:
                  charPct > 0.9
                    ? 'var(--error)'
                    : 'linear-gradient(90deg, var(--accent), var(--accent-bright))',
              }}
            />
          </div>

          <textarea
            id="prompt-textarea"
            className="prompt-textarea"
            rows={8}
            value={prompt}
            onChange={(e) => onPromptChange(e.target.value)}
            placeholder="Build a SaaS landing page with a hero section, feature cards, and pricing table..."
            disabled={isGenerating}
            maxLength={maxChars}
          />
        </div>

        {/* Presets */}
        <div>
          <p className="text-[10px] font-600 uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>
            Quick Presets
          </p>
          <div className="flex flex-wrap gap-1.5">
            {PRESETS.map((preset, i) => (
              <button
                key={preset.label}
                id={`preset-${preset.label.toLowerCase().replace(/\s+/g, '-')}`}
                className={`preset-chip animate-fade-in-up stagger-${i + 1}`}
                onClick={() => onPromptChange(preset.prompt)}
                disabled={isGenerating}
                title={preset.prompt.slice(0, 100) + '…'}
              >
                <span>{preset.icon}</span>
                <span>{preset.label}</span>
                <ChevronRight size={10} style={{ opacity: 0.4 }} />
              </button>
            ))}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div
            className="rounded-lg px-3.5 py-2.5 text-xs leading-relaxed animate-scale-in"
            style={{
              background: 'rgba(248,113,113,0.06)',
              border: '1px solid rgba(248,113,113,0.15)',
              color: 'var(--error)',
            }}
          >
            ⚠️ {error}
          </div>
        )}

        {/* Stats */}
        {(tokenCount > 0 || isGenerating) && (
          <div
            className="rounded-lg px-3.5 py-3 animate-fade-in"
            style={{
              background: 'rgba(129,140,248,0.04)',
              border: '1px solid rgba(129,140,248,0.1)',
            }}
          >
            <p className="text-[10px] font-600 uppercase tracking-wider mb-2" style={{ color: 'var(--accent)' }}>
              Generation Stats
            </p>
            <div className="grid grid-cols-2 gap-1.5">
              <StatRow label="Tokens" value={tokenCount > 0 ? tokenCount.toString() : '—'} />
              <StatRow
                label="TTFT"
                value={ttft != null ? `${ttft.toFixed(0)}ms` : isGenerating ? '…' : '—'}
              />
              <StatRow
                label="Speed"
                value={tokensPerSec != null ? `${tokensPerSec.toFixed(1)} t/s` : isGenerating ? '…' : '—'}
              />
              <StatRow
                label="Total"
                value={totalTime != null ? `${(totalTime / 1000).toFixed(1)}s` : isGenerating ? '…' : '—'}
              />
            </div>
          </div>
        )}
      </div>

      {/* ── Generate / Cancel button ────────────────────────── */}
      <div
        className="flex-none px-4 py-4"
        style={{ borderTop: '1px solid var(--border)' }}
      >
        {isGenerating ? (
          <button
            id="btn-cancel"
            onClick={onCancel}
            className="w-full py-3 rounded-lg flex items-center justify-center gap-2 text-sm font-600 transition-all duration-200"
            style={{
              background: 'rgba(248,113,113,0.06)',
              border: '1px solid rgba(248,113,113,0.18)',
              color: 'var(--error)',
            }}
          >
            <Square size={14} />
            Stop Generating
          </button>
        ) : (
          <button
            id="btn-generate"
            onClick={onGenerate}
            disabled={!canGenerate}
            className="btn-generate w-full py-3 flex items-center justify-center gap-2"
          >
            <Zap size={15} />
            Generate Website
          </button>
        )}
      </div>
    </aside>
  );
}

/* ── Tiny helper ─────────────────────────────────────────── */
function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="flex items-center justify-between rounded-md border px-2.5 py-1.5"
      style={{
        borderColor: 'var(--border)',
        background: 'rgba(10,10,18,0.5)',
      }}
    >
      <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span className="text-[11px] font-600 mono" style={{ color: 'var(--text-secondary)' }}>{value}</span>
    </div>
  );
}
