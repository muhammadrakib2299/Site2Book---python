# Site2Book

Convert any website into a clean, downloadable PDF eBook — with table of contents, cover page, and bookmarks.

Paste a URL, pick how many pages, and get back a single polished PDF you can read offline.

## How it works

1. Crawls internal pages (same origin, path-prefix scoped, respects `robots.txt`)
2. Renders each page in a real Chromium browser via Playwright
3. Cleans ads, nav, cookie banners, and other noise
4. Merges everything into one PDF with a cover page, TOC, and clickable bookmarks

## Tech stack

| Layer | Choice |
|---|---|
| API | FastAPI (Python 3.12) |
| Browser | Playwright (Chromium) |
| PDF merge | pypdf |
| Content cleanup | Mozilla Readability |
| Frontend | Next.js 15 (App Router) + TypeScript |
| Styling | Tailwind + shadcn/ui |
| Database | SQLite (via SQLModel) |
| Progress | Server-Sent Events (no polling, no job queue) |
| Deploy | Docker → Fly.io / Railway |

## Repository layout

```
site2book/
├── apps/
│   ├── api/                      # FastAPI backend
│   │   ├── main.py
│   │   ├── convert.py            # SSE streaming endpoint
│   │   ├── crawler.py            # scoping, dedupe, robots.txt
│   │   ├── renderer.py           # Playwright pool
│   │   ├── ebook.py              # cover, TOC, bookmarks, merge
│   │   ├── storage.py            # local (MVP) → S3-compatible interface
│   │   └── db.py                 # SQLite
│   └── web/                      # Next.js frontend
│       ├── app/
│       │   ├── page.tsx          # URL input
│       │   └── convert/page.tsx  # live progress + download
│       └── lib/sse.ts
├── docker/
│   └── Dockerfile                # Playwright base image
├── compose.yml
├── overview.txt                  # original project spec
├── TODO.md                       # phased build plan
└── README.md
```

## API

```
POST  /api/convert          → SSE stream of progress events; ends with download token
GET   /api/files/{token}    → signed URL, 24h expiry
GET   /api/preview?url=...  → optional: title + favicon + og:image for UX
```

### Convert request

```json
{
  "url": "https://example.com/docs/",
  "max_pages": 20,
  "same_domain_only": true,
  "include_subpages": true
}
```

### Convert event stream (NDJSON over SSE)

```json
{"event":"crawling","url":"https://example.com/docs/intro"}
{"event":"rendering","page":3,"total":12}
{"event":"merging"}
{"event":"done","download_url":"/api/files/abc123.pdf","pages":12,"size_bytes":2847291}
```

## Local development

### Prerequisites

- Python 3.12+
- Node.js 20+
- ~1 GB free disk (Playwright Chromium)

### Setup

```bash
# Backend
cd apps/api
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000.

### Docker

```bash
docker compose up --build
```

## Design decisions

- **SSE over polling** — progress streams on one open connection. No `job_id`, no `/status` endpoint, no background worker for MVP.
- **SQLite over Postgres/Redis** — one file, zero ops, handles MVP scale forever.
- **Path-prefix crawl scoping** — if you paste `docs.site.com/guide/`, only links under `/guide/` are followed. Eliminates 80% of crawl noise.
- **TOC + cover from day one** — these are what make it an eBook instead of a pile of PDFs.
- **No Celery** — added only when real concurrency pressure shows up.

## Limits

- Max 50 pages per conversion (raised later with auth)
- Max 15s render timeout per page
- Rate limit: 3 conversions per IP per hour (unauthenticated)
- Paywalled and login-gated pages are detected and skipped
- Respects `robots.txt` and `crawl-delay`

## Roadmap

See [TODO.md](./TODO.md) for the phased build plan.

Later:
- EPUB export
- AI summary per chapter
- Scheduled re-crawls
- User accounts + history
- S3 storage

## License

TBD
