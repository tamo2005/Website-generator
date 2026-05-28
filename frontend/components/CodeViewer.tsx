'use client';

import { useState, useRef, useCallback } from 'react';
import { Copy, Download, CheckCheck } from 'lucide-react';

/* ────────────────────────────────────────────────────────────
   Props
──────────────────────────────────────────────────────────── */
interface CodeViewerProps {
  code: string;
}

/* ────────────────────────────────────────────────────────────
   Component
──────────────────────────────────────────────────────────── */
export default function CodeViewer({ code }: CodeViewerProps) {
  const [copied, setCopied] = useState(false);
  const codeRef = useRef<HTMLPreElement>(null);

  /* ── Copy ──────────────────────────────────────────────── */
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for environments without clipboard API
      const el = document.createElement('textarea');
      el.value = code;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [code]);

  /* ── Download ──────────────────────────────────────────── */
  const handleDownload = useCallback(() => {
    const blob = new Blob([code], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'generated-site.html';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [code]);

  /* ── Line count ────────────────────────────────────────── */
  const lineCount = code.split('\n').length;
  const charCount = code.length;

  if (!code) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Generated code will appear here…
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div
        className="flex-none flex items-center justify-between px-4 py-2.5"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <div className="flex items-center gap-3">
          <span className="text-xs mono" style={{ color: 'var(--text-muted)' }}>
            {lineCount} lines · {charCount.toLocaleString()} chars
          </span>
          <span
            className="px-2 py-0.5 rounded text-[10px] font-600 uppercase tracking-wider"
            style={{ background: 'rgba(99,102,241,0.15)', color: '#818cf8' }}
          >
            HTML
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            id="btn-copy-code"
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-500 transition-all duration-150"
            style={{
              background: copied ? 'rgba(52,211,153,0.1)' : 'rgba(255,255,255,0.05)',
              border: `1px solid ${copied ? 'rgba(52,211,153,0.3)' : 'var(--border)'}`,
              color: copied ? 'var(--success)' : 'var(--text-secondary)',
            }}
          >
            {copied ? <CheckCheck size={12} /> : <Copy size={12} />}
            {copied ? 'Copied!' : 'Copy'}
          </button>

          <button
            id="btn-download-code"
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-500 transition-all duration-150"
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid var(--border)',
              color: 'var(--text-secondary)',
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)';
              (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(99,102,241,0.4)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)';
              (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border)';
            }}
          >
            <Download size={12} />
            Download .html
          </button>
        </div>
      </div>

      {/* Code */}
      <div className="flex-1 overflow-auto flex">
        {/* Line numbers */}
        <div
          className="flex-none py-4 pl-4 pr-3 text-right select-none"
          style={{
            borderRight: '1px solid var(--border)',
            background: 'rgba(0,0,0,0.2)',
          }}
        >
          {Array.from({ length: lineCount }, (_, i) => (
            <div
              key={i}
              className="text-[11px] mono leading-[1.6] block"
              style={{ color: 'var(--text-muted)', opacity: 0.6 }}
            >
              {i + 1}
            </div>
          ))}
        </div>

        {/* Code content */}
        <div className="flex-1 overflow-auto">
          <pre
            ref={codeRef}
            className="code-block p-4 min-h-full"
            aria-label="Generated HTML code"
          >
            <code>{code}</code>
          </pre>
        </div>
      </div>
    </div>
  );
}
