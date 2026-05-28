'use client';

import { useCallback, useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import DOMPurify from 'dompurify';

interface ExportButtonProps {
  code: string;
}

const PREVIEW_CSS_URL = '/preview-tailwind.css';

function buildDocument(html: string, stylesheetHref: string) {
  const safe = DOMPurify.sanitize(html, {
    ADD_TAGS: ['style', 'link'],
    ADD_ATTR: ['class', 'style', 'href', 'rel', 'src', 'alt', 'id', 'data-*'],
  });

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="stylesheet" href="${stylesheetHref}" />
  <style>
    html, body { margin: 0; min-height: 100%; background: #020617; }
    body { color: #e2e8f0; }
  </style>
</head>
<body>${safe}</body>
</html>`;
}

async function fetchPreviewCss() {
  const response = await fetch(PREVIEW_CSS_URL, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Failed to load ${PREVIEW_CSS_URL}`);
  }
  return response.text();
}

export default function ExportButton({ code }: ExportButtonProps) {
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = useCallback(async () => {
    if (!code.trim()) return;

    setIsExporting(true);
    try {
      const [css, zipClass] = await Promise.all([
        fetchPreviewCss(),
        import('jszip'),
      ]);

      const zip = new zipClass.default();
      zip.file('index.html', buildDocument(code, './preview-tailwind.css'));
      zip.file('preview-tailwind.css', css);

      const blob = await zip.generateAsync({ type: 'blob' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'generated-site.zip';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setIsExporting(false);
    }
  }, [code]);

  return (
    <button
      id="btn-export-site"
      onClick={handleExport}
      disabled={!code.trim() || isExporting}
      className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all duration-200"
      style={{
        borderColor: 'var(--border)',
        background: 'rgba(255,255,255,0.03)',
        color: 'var(--text-secondary)',
      }}
    >
      {isExporting ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
      Export ZIP
    </button>
  );
}