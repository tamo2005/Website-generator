# AI Website Generator Roadmap (Next.js 14 + Tailwind + FastAPI/LangChain)

This guide gives you a **step-by-step setup** and implementation plan for building an AI website generator with:
- **Frontend:** Next.js 14 + Tailwind CSS
- **Backend:** Python FastAPI + LangChain + Hugging Face
- **Deployment:** Vercel (frontend) + Railway (backend)

---

## 1) Local Dev-Environment Setup (Do This First)

## 1.1 Install prerequisites
- Node.js **20+** (or Node 22 LTS)
- Python **3.10+**
- VS Code
- Git

### Recommended VS Code extensions
- Tailwind CSS IntelliSense
- ESLint
- Python (Pylance)
- Ruff

## 1.2 Create project structure

```bash
mkdir ai-site-generator && cd ai-site-generator
mkdir frontend backend
```

## 1.3 Setup backend (FastAPI + LangChain)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install fastapi uvicorn langchain-core langchain-huggingface python-dotenv
pip freeze > requirements.txt
```

Create `/backend/.env`:

```env
HF_TOKEN=your_huggingface_token
MODEL_ID=meta-llama/Meta-Llama-3-70B-Instruct
ALLOWED_ORIGIN=http://localhost:3000
```

## 1.4 Setup frontend (Next.js 14 + Tailwind)

```bash
cd ../frontend
npx create-next-app@14 . --ts --tailwind --app --eslint
npm install lucide-react
npm install dompurify
```

Create `/frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Also create `/frontend/public/preview-tailwind.css` from your built Tailwind output for safe iframe previews without runtime script execution.

## 1.5 Run both services locally

Backend:
```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm run dev
```

Open `http://localhost:3000`.

---

## 2) Component-by-Component Architecture

Use this UI structure to keep generation and rendering stable:

```text
WorkspaceContainer
├── PromptPanel      (prompt input + presets + submit)
├── CodeViewer       (raw generated HTML/Tailwind, copy/download)
└── PreviewPane      (sandbox iframe srcDoc rendering)
```

### Responsibilities
- **WorkspaceContainer**
  - Owns global state: `prompt`, `streamedCode`, `renderedCode`, `isGenerating`, `error`
  - Starts/cancels streaming requests
- **PromptPanel**
  - Textarea + preset chips + Generate button
  - Disables controls while generation is active
- **CodeViewer**
  - Shows raw model output
  - Optional “sanitize output” toggle
- **PreviewPane**
  - Renders sanitized HTML into `iframe.srcDoc`
  - Isolated sandbox to protect parent app

Backend modules:
- `main.py` (FastAPI app, CORS, endpoints)
- `llm_service.py` (LangChain + HF call + prompt template)
- `streaming.py` (SSE formatter / token sanitation)

---

## 3) Learning Path (in order)

### Phase A: Prompting for code synthesis
Learn to craft strict prompts that return only executable code.

System prompt baseline:
- “Return only valid HTML with Tailwind classes. No markdown fences. No explanations.”

### Phase B: Reactive state for real-time preview
Learn token streaming patterns:
- `ReadableStream` parsing
- append to buffer state
- debounce heavy preview updates
- keep UI responsive during token flow

### Phase C: Deployment + operations
- Frontend on **Vercel** (fast global edge delivery)
- Backend on **Railway** (FastAPI SSE/WebSocket capable)
- Configure CORS to production origin only
- Add rate limiting and request timeouts

---

## 4) Core React ↔ AI API Flow

## 4.1 FastAPI streaming endpoint (`backend/main.py`)

```python
import os
import re
from pydantic import BaseModel, Field
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = HuggingFaceEndpoint(
    repo_id=os.getenv("MODEL_ID", "meta-llama/Meta-Llama-3-70B-Instruct"),
    huggingfacehub_api_token=os.getenv("HF_TOKEN"),
    temperature=0.2,
    streaming=True,
)

SYSTEM_PROMPT = (
    "You are a senior frontend engineer. Return ONLY valid HTML with Tailwind classes. "
    "Do not include markdown fences, explanations, or backticks.\nUser request: "
)
MAX_PROMPT_CHARS = int(os.getenv("MAX_PROMPT_CHARS", "12000"))

class GenerateRequest(BaseModel):
    # Keep configurable for different model context windows and provider payload limits.
    prompt: str = Field(min_length=3, max_length=MAX_PROMPT_CHARS)

async def stream_html(prompt: str):
    async for chunk in llm.astream(SYSTEM_PROMPT + prompt):
        text = re.sub(r"```(?:html)?", "", str(chunk), flags=re.IGNORECASE)
        yield f"data: {text}\n\n"

@app.post("/api/generate")
async def generate(payload: GenerateRequest):
    return StreamingResponse(stream_html(payload.prompt), media_type="text/event-stream")
```

## 4.2 Next.js client streaming (`frontend/app/page.tsx`)

```tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import DOMPurify from 'dompurify';

const initialMarkup =
  '<div class="p-8 text-center text-slate-400">Your site preview will appear here.</div>';
const PREVIEW_DEBOUNCE_MS = 100;

export default function Page() {
  const [prompt, setPrompt] = useState('');
  const [code, setCode] = useState(initialMarkup);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Tune PREVIEW_DEBOUNCE_MS upward if low-end devices struggle with iframe repaints.
  useEffect(() => {
    const t = setTimeout(() => {
      if (!iframeRef.current) return;
      const safeCode = DOMPurify.sanitize(code);
      const tailwindStylesheet = '<link rel="stylesheet" href="/preview-tailwind.css" />';
      iframeRef.current.srcdoc = `${tailwindStylesheet}<body class="bg-slate-50">${safeCode}</body>`;
    }, PREVIEW_DEBOUNCE_MS);

    return () => clearTimeout(t);
  }, [code]);

  const generate = async () => {
    setLoading(true);
    setError('');
    setCode('<div class="animate-pulse p-8">Generating layout...</div>');

    try {
      const base = process.env.NEXT_PUBLIC_API_URL;
      const res = await fetch(`${base}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });
      if (!res.body) throw new Error('No response stream');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffered = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffered += decoder.decode(value, { stream: true });

        const events = buffered.split('\n\n');
        buffered = events.pop() ?? '';

        for (const evt of events) {
          const line = evt.split('\n').find((l) => l.startsWith('data: '));
          if (!line) continue;
          const token = line.replace(/^data:\s*/, '');
          setCode((prev) => prev + token);
        }
      }
    } catch (e) {
      console.error(e);
      const msg = e instanceof Error ? e.message : 'Unknown error';
      setError(`Generation failed (${msg}). Retry or reduce prompt size.`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="grid h-screen grid-cols-[320px_1fr] bg-slate-900 text-white">
      <section className="flex flex-col gap-3 border-r border-slate-800 p-4">
        <h1 className="text-sm uppercase tracking-wider text-slate-400">AI Website Generator</h1>
        <textarea
          className="min-h-[220px] rounded border border-slate-700 bg-slate-800 p-3 text-sm"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Build a SaaS landing page for a note-taking app..."
        />
        <button
          onClick={generate}
          disabled={loading || !prompt.trim()}
          className="rounded bg-blue-600 py-2 text-sm font-medium disabled:bg-slate-700"
        >
          {loading ? 'Generating...' : 'Generate'}
        </button>
        {error ? <p className="text-xs text-red-400">{error}</p> : null}
      </section>

      <section className="p-4">
        <iframe
          ref={iframeRef}
          className="h-full w-full rounded bg-white"
          title="Preview"
          // No extra permissions: do not allow scripts, same-origin, forms, or popups.
          sandbox=""
        />
      </section>
    </main>
  );
}
```

---

## 5) Bridging Frontend ↔ LLM Latency Gap (Critical)

1. **Show immediate optimistic UI**
   - Inject a skeleton into preview at click time.
2. **Stream, don’t wait for full completion**
   - Use SSE or chunked HTTP response.
3. **Debounce iframe updates (~100ms)**
   - Prevent repaint on every token.
4. **Use dual buffers**
   - `streamedCode` for token appends, `renderedCode` for safe preview updates.
5. **Sanitize model artifacts**
   - Remove stray markdown fences and partial junk.
6. **Add cancellation**
   - `AbortController` when user submits another prompt.
7. **Measure performance**
   - Track TTFT, tokens/sec, total generation time.

---

## 6) Deployment Checklist

### Frontend (Vercel)
- Import repo in Vercel
- Set `NEXT_PUBLIC_API_URL` to Railway backend URL
- Deploy `frontend/`

### Backend (Railway)
- Deploy `backend/`
- Add env vars: `HF_TOKEN`, `MODEL_ID`, `ALLOWED_ORIGIN`
- Expose port + start command:
  `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Security & reliability
- Restrict CORS to Vercel domain
- Add API rate limits
- Add request size limits and prompt validation
- Log errors and latency metrics

---

## 7) Suggested Build Order (Step-by-Step)

1. Bootstrap frontend and backend projects
2. Add `/api/generate` SSE endpoint in FastAPI
3. Create Next.js workspace layout (PromptPanel/Preview/CodeViewer)
4. Wire frontend stream reader to backend endpoint
5. Add markdown-fence sanitizer + debounce preview rendering
6. Add loading skeleton + abort/cancel support
7. Add preset prompts and reusable templates
8. Deploy frontend to Vercel, backend to Railway
9. Lock CORS + env vars + basic rate limiting
10. Measure TTFT and optimize prompts/model choices
