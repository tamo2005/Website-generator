'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import DOMPurify from 'dompurify';
import { Monitor, Code2, Loader2, ExternalLink } from 'lucide-react';
import CodeViewer from './CodeViewer';
import ExportButton from './ExportButton';

/* ────────────────────────────────────────────────────────────
   Constants
──────────────────────────────────────────────────────────── */
const DEBOUNCE_MS = 120;

const SKELETON_HTML = `
<div style="font-family:system-ui,sans-serif;padding:32px;background:#f8fafc;min-height:100vh">
  <div style="max-width:900px;margin:0 auto">
    <div style="height:16px;border-radius:8px;background:linear-gradient(90deg,#e2e8f0,#f1f5f9,#e2e8f0);background-size:200% 100%;animation:shimmer 1.5s infinite;margin-bottom:12px;width:60%"></div>
    <div style="height:10px;border-radius:6px;background:linear-gradient(90deg,#e2e8f0,#f1f5f9,#e2e8f0);background-size:200% 100%;animation:shimmer 1.5s infinite;margin-bottom:8px;width:40%"></div>
    <div style="height:10px;border-radius:6px;background:linear-gradient(90deg,#e2e8f0,#f1f5f9,#e2e8f0);background-size:200% 100%;animation:shimmer 1.5s infinite;margin-bottom:32px;width:50%"></div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:32px">
      ${[80, 65, 75].map(() => `<div style="height:120px;border-radius:12px;background:linear-gradient(90deg,#e2e8f0,#f1f5f9,#e2e8f0);background-size:200% 100%;animation:shimmer 1.5s infinite"></div>`).join('')}
    </div>
    <div style="height:10px;border-radius:6px;background:linear-gradient(90deg,#e2e8f0,#f1f5f9,#e2e8f0);background-size:200% 100%;animation:shimmer 1.5s infinite;margin-bottom:8px"></div>
    <div style="height:10px;border-radius:6px;background:linear-gradient(90deg,#e2e8f0,#f1f5f9,#e2e8f0);background-size:200% 100%;animation:shimmer 1.5s infinite;margin-bottom:8px;width:85%"></div>
    <div style="height:10px;border-radius:6px;background:linear-gradient(90deg,#e2e8f0,#f1f5f9,#e2e8f0);background-size:200% 100%;animation:shimmer 1.5s infinite;width:70%"></div>
  </div>
  <style>
    @keyframes shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}
  </style>
</div>`;

const EMPTY_HTML = `
<div style="
  font-family:system-ui,sans-serif;
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  min-height:100vh;
  background:#f8fafc;
  color:#94a3b8;
  gap:12px;
  text-align:center;
  padding:32px;
">
  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.5">
    <rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/>
    <line x1="12" y1="17" x2="12" y2="21"/>
  </svg>
  <p style="margin:0;font-size:15px;font-weight:500;color:#64748b">Your preview will appear here</p>
  <p style="margin:0;font-size:13px">Describe your site and click <strong>Generate Website</strong></p>
</div>`;

/* ────────────────────────────────────────────────────────────
   Props
──────────────────────────────────────────────────────────── */
interface PreviewPaneProps {
  code: string;
  isGenerating: boolean;
}

type Tab = 'preview' | 'code';

/* ────────────────────────────────────────────────────────────
   Component
──────────────────────────────────────────────────────────── */
export default function PreviewPane({ code, isGenerating }: PreviewPaneProps) {
  const [activeTab, setActiveTab] = useState<Tab>('preview');
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* ── Build iframe srcdoc ────────────────────────────────── */
  const buildSrcdoc = useCallback((html: string, loading: boolean): string => {
    const stylesheetHref = typeof window !== 'undefined'
      ? new URL('/preview-tailwind.css', window.location.origin).href
      : '/preview-tailwind.css';

    let content: string;
    if (loading && !html) {
      content = SKELETON_HTML;
    } else if (!html) {
      content = EMPTY_HTML;
    } else {
      const safe = DOMPurify.sanitize(html, {
        ADD_TAGS: ['style', 'link'],
        ADD_ATTR: ['class', 'style', 'href', 'rel', 'src', 'alt', 'id', 'data-*'],
        FORCE_BODY: false,
      });
      content = safe;
    }

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="${stylesheetHref}">
  <style>
    *{box-sizing:border-box}
    html,body{margin:0;min-height:100%;background:#020617;color:#e2e8f0}
    body{overflow:auto}
  </style>
</head>
<body>${content}</body>
</html>`;
  }, []);

  /* ── Debounced iframe update ─────────────────────────────── */
  useEffect(() => {
    if (activeTab !== 'preview') return;

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (!iframeRef.current) return;
      iframeRef.current.srcdoc = buildSrcdoc(code, isGenerating);
    }, DEBOUNCE_MS);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [code, isGenerating, activeTab, buildSrcdoc]);

  /* ── Open in new tab ──────────────────────────────────────── */
  const handleOpenInTab = useCallback(() => {
    if (!code) return;
    const safe = DOMPurify.sanitize(code, {
      ADD_TAGS: ['style'],
      ADD_ATTR: ['class', 'style'],
    });
    const html = buildSrcdoc(safe, false);
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }, [code, buildSrcdoc]);

  return (
    <div className="flex flex-col h-full overflow-hidden animate-fade-in">
      {/* ── Tab bar ─────────────────────────────────────────── */}
      <div
        className="flex-none flex items-center justify-between px-4 py-2.5"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <div className="flex items-center gap-1.5">
          <button
            id="tab-preview"
            className={`tab-btn flex items-center gap-1.5 ${activeTab === 'preview' ? 'active' : ''}`}
            onClick={() => setActiveTab('preview')}
          >
            <Monitor size={13} />
            Preview
          </button>
          <button
            id="tab-code"
            className={`tab-btn flex items-center gap-1.5 ${activeTab === 'code' ? 'active' : ''}`}
            onClick={() => setActiveTab('code')}
          >
            <Code2 size={13} />
            Code
            {code && (
              <span
                className="px-1.5 py-0.5 rounded-full text-[9px] font-600"
                style={{ background: 'rgba(99,102,241,0.2)', color: '#a5b4fc' }}
              >
                {code.split('\n').length}L
              </span>
            )}
          </button>
        </div>

            <ExportButton code={code} />

        <div className="flex items-center gap-2">
          {/* Generating indicator */}
          {isGenerating && (
            <div className="flex items-center gap-1.5 animate-fade-in">
              <Loader2 size={12} className="animate-spin" style={{ color: '#818cf8' }} />
              <span className="text-[11px] font-500" style={{ color: '#818cf8' }}>
                Generating…
              </span>
            </div>
          )}

          {/* Open in new tab */}
          {code && (
            <button
              id="btn-open-in-tab"
              onClick={handleOpenInTab}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-600 transition-all duration-150"
              style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid var(--border)',
                color: 'var(--text-secondary)',
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)';
              }}
              title="Open preview in new tab"
            >
              <ExternalLink size={11} />
              Open
            </button>
          )}
        </div>
      </div>

      {/* ── Content area ────────────────────────────────────── */}
      <div className="flex-1 overflow-hidden relative">
        {/* Preview tab */}
        <div
          className={`absolute inset-0 transition-opacity duration-200 ${activeTab === 'preview' ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}
        >
          <iframe
            ref={iframeRef}
            id="preview-iframe"
            title="Generated website preview"
            className="w-full h-full"
            sandbox="allow-scripts"
            style={{ border: 'none', background: '#020617' }}
          />
        </div>

        {/* Code tab */}
        <div
          className={`absolute inset-0 overflow-hidden transition-opacity duration-200 ${activeTab === 'code' ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}
          style={{ background: 'rgba(0,0,0,0.3)' }}
        >
          <CodeViewer code={code} />
        </div>
      </div>
    </div>
  );
}
