# apps/web

Next.js 15 frontend for Site2Book — URL input form and live progress UI.

## Setup

```bash
cd apps/web
cp .env.example .env.local   # optional; defaults to http://localhost:8000
npm install
npm run dev
```

Open http://localhost:3000. The API must be running at the URL in
`NEXT_PUBLIC_API_BASE` (default `http://localhost:8000`).

## Pages

- `/` — URL form with options (max pages, include subdomains)
- `/convert?url=...` — live progress via SSE, download link on completion

## Data flow

`src/lib/sse.ts` POSTs to `/api/convert` and parses the SSE stream by
hand (native `EventSource` can't POST). Next.js rewrites `/api/*` to
the Python API so the browser sees everything same-origin — no CORS
preflight in dev.
