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

Web: http://localhost:3000 · API: http://localhost:8000/api/health

## Deployment

The app is two services: a Python API (FastAPI + Playwright Chromium) and a
Next.js frontend. They deploy independently.

> **Reality check:** Playwright Chromium uses ~1 GB RAM at peak. That rules
> out most 512 MB free tiers (Render, small Railway). Below are the free
> paths that actually work.

### 🥇 Recommended free path — Vercel + Hugging Face Spaces

Why this combo: Vercel is built for Next.js, and Hugging Face Spaces gives
**16 GB RAM, 2 vCPU, always-on** on the free tier — way more than we need
for Playwright. Total time: ~15 minutes.

#### 1. Backend → Hugging Face Space

1. Create a new Space at <https://huggingface.co/new-space> with SDK =
   **Docker** (blank template).
2. Clone the Space repo locally.
3. Copy these into the Space root:
   - `apps/` (the whole directory)
   - `docker/api.Dockerfile` → rename to `Dockerfile`
4. Edit the Dockerfile's last two lines to use port 7860 (HF requirement):
   ```dockerfile
   EXPOSE 7860
   CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
   ```
5. In the Space's **Settings → Variables and secrets**, add:
   ```
   SITE2BOOK_ALLOWED_ORIGINS=https://<your-vercel-url>.vercel.app
   SITE2BOOK_MAX_PAGES=50
   ```
6. `git push` to the Space — HF builds and deploys automatically.
   The API is live at `https://<username>-<space-name>.hf.space`.

#### 2. Frontend → Vercel

1. Import the GitHub repo at <https://vercel.com/new>.
2. **Root directory:** `apps/web`
3. **Environment variables:**
   ```
   NEXT_PUBLIC_API_BASE=https://<username>-<space-name>.hf.space
   ```
4. Click Deploy.
5. Copy the resulting Vercel URL back into the Space's
   `SITE2BOOK_ALLOWED_ORIGINS` env var so CORS accepts it.

### 🥈 Alternative — Render (simpler, but tight RAM)

- Render free tier: 512 MB RAM, spins down after 15 min idle, 30–60 s cold
  start on wake.
- Will OOM on heavy-JS pages. OK for demos against simple sites
  (`example.com`, static blogs). Not for daily use.
- Setup: Render → New Web Service → Connect GitHub → **Docker** →
  Dockerfile path `docker/api.Dockerfile` → Instance type: Free.

### 🥉 Most powerful free — Oracle Cloud Always Free ARM VM

- **4 ARM cores + 24 GB RAM, free forever.**
- `git clone` the repo on the VM, `docker compose up -d`, done.
- You manage the VM (TLS, updates). Use Cloudflare Tunnel for free TLS +
  a `*.trycloudflare.com` URL without opening ports.

### 💸 Nearly free — Fly.io (~$5/month)

The repo ships a ready-to-use `fly.toml` targeting a 2 GB shared-CPU
machine. Fly no longer has a free tier, but this is the cheapest managed
path with the cleanest deploy story:

```bash
fly launch --copy-config --no-deploy
fly volumes create site2book_data --size 1 --region lhr
fly deploy
```

Then point your Vercel frontend's `NEXT_PUBLIC_API_BASE` at
`https://<your-app>.fly.dev`.

### Single-host deploy (any VPS)

If you already have a server:

```bash
git clone https://github.com/muhammadrakib2299/Site2Book---python.git
cd Site2Book---python
docker compose up -d --build
```

Frontend: `:3000` · API: `:8000`. Put a reverse proxy (Caddy, nginx,
Traefik) in front for TLS.

### Environment variables reference

Set these on whichever host runs the API:

| Var | Default | Purpose |
|---|---|---|
| `SITE2BOOK_DATA_DIR` | `./data` | SQLite + generated PDFs (mount a volume here) |
| `SITE2BOOK_ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated list of frontend origins |
| `SITE2BOOK_MAX_PAGES` | `50` | Hard ceiling per conversion |
| `SITE2BOOK_MAX_CONCURRENT_JOBS` | `2` | Playwright pool size |
| `SITE2BOOK_RATE_LIMIT_PER_HOUR` | `3` | Per-IP limit |
| `SITE2BOOK_FILE_TTL_HOURS` | `24` | PDF retention |

Frontend needs one:

| Var | Example | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_BASE` | `https://yourname-site2book.hf.space` | Where the browser calls the API |

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
