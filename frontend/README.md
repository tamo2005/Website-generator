# Frontend

This folder contains the Next.js app for the website generator workspace.

## Run

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
npm run build:preview
```

## Environment

Create `frontend/.env.local` with:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Notes

- The preview iframe uses `public/preview-tailwind.css`.
- The export button packages the generated HTML and preview stylesheet into a ZIP file.
- The UI is designed to pair with the FastAPI backend in `../backend`.
