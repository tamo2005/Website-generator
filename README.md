# Website Generator

Build and preview polished landing pages, dashboards, and marketing sites from a single prompt.

This repository pairs a Next.js frontend with a FastAPI backend so you can generate a page, inspect the code, preview the result, and export a portable ZIP bundle with one workflow.

## What it does

- Generates responsive HTML using a streaming LLM backend.
- Renders the result inside a sandboxed preview iframe.
- Shows the raw generated markup side by side with the live preview.
- Exports a complete ZIP package containing `index.html` and `preview-tailwind.css`.
- Uses a local Tailwind CSS build for preview and export, so the final output is portable.

## Highlights

- Fast prompt-to-preview loop with streamed output.
- Local preview stylesheet generation for consistent rendering.
- Clean export flow for sharing or deploying generated pages.
- Dark, high-contrast interface built for focused editing.
- Backend and frontend run independently, so you can swap models or deploy them separately.

## Tech Stack

- Frontend: Next.js 14, React, Tailwind CSS, DOMPurify, JSZip
- Backend: FastAPI, OpenRouter, Server-Sent Events
- Output: HTML plus a generated Tailwind stylesheet

## Project Layout

```text
backend/
  main.py              FastAPI app, generation endpoint, export endpoint
  llm_service.py       OpenRouter streaming client and fallback renderer
  streaming.py         SSE formatting and token cleanup helpers

frontend/
  app/
    page.tsx           Main workspace shell
    layout.tsx         Root layout and fonts
    globals.css        Brutal dark theme and shared UI tokens
  components/
    PromptPanel.tsx    Prompt input, presets, and generation controls
    PreviewPane.tsx    Live preview and code tabs
    CodeViewer.tsx     Raw HTML viewer with copy/download tools
    ExportButton.tsx   ZIP export action
    StatusBar.tsx      Runtime status and generation stats
  preview-input.css    Tailwind input used to build preview CSS
  public/preview-tailwind.css  Generated stylesheet for preview/export
```

## Quick Start

Install dependencies:

```bash
cd backend
python -m pip install -r requirements.txt

cd ../frontend
npm install
```

Create your environment files:

```env
# backend/.env
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=moonshotai/kimi-k2.6:free
OPENROUTER_SITE_URL=http://localhost:3000
OPENROUTER_APP_NAME=Website Generator
OPENROUTER_REASONING_ENABLED=false
PREVIEW_CSS_PATH=../frontend/public/preview-tailwind.css
ALLOWED_ORIGIN=http://localhost:3000,http://localhost:3001
```

```env
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start both services:

```bash
# terminal 1
cd backend
uvicorn main:app --reload --port 8000

# terminal 2
cd frontend
npm run dev
```

If port `3000` is busy, Next.js will usually move to `3001` automatically.

## Preview CSS Pipeline

The preview iframe does not depend on a CDN script. Instead, the app uses a local stylesheet generated from Tailwind.

Build it with:

```bash
cd frontend
npm run build:preview
```

This produces:

- `frontend/public/preview-tailwind.css`

That file is used by:

- the live preview iframe
- the export ZIP package

## Export Flow

The preview toolbar includes an `Export ZIP` action that packages:

- `index.html`
- `preview-tailwind.css`

The backend also exposes `POST /api/export` if you want to generate the same ZIP from server-side code.

## Backend API

### `GET /api/health`
Returns the active model and prompt limit.

### `POST /api/generate`
Streams generated HTML as Server-Sent Events.

### `POST /api/export`
Returns a ZIP archive with the rendered HTML document and the preview stylesheet.

## Frontend Scripts

```bash
npm run dev           # start local dev server
npm run build         # production build
npm run build:preview # generate preview-tailwind.css
npm run start         # run production build
```

## Security Notes

- Keep real API keys out of version control.
- Rotate any token that has been pasted into chat or logs.
- Keep the iframe sandboxed unless a feature truly needs more permissions.
- Use the export ZIP for sharing the generated page without exposing your backend.

## Verification

Recommended checks:

```bash
cd frontend
npm run build:preview
npm run build

cd ../backend
python -m py_compile main.py llm_service.py streaming.py
```

## Current Behavior

- The workspace streams HTML into the preview and code panes.
- The fallback renderer keeps the app usable if the model provider rate-limits a request.
- The exported ZIP is ready to open locally or hand off to another developer.

## Notes

- The backend is configured for OpenRouter.
- The design system is intentionally dark, sharp, and high-contrast.
- The output is optimized for landing pages, dashboards, and editorial layouts.
