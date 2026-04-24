# apps/api

FastAPI backend for Site2Book. CLI for local use and an HTTP API with SSE streaming.

## Setup

Run from the repository root.

```bash
python -m venv .venv
.venv\Scripts\activate              # Windows
# source .venv/bin/activate         # macOS / Linux

pip install -r apps/api/requirements.txt
playwright install chromium
```

## CLI

```bash
# single page → PDF
python -m apps.api.cli convert https://example.com -o out.pdf

# crawl a site and print the ordered page list
python -m apps.api.cli crawl https://example.com/docs/ --max-pages 20

# full eBook: crawl + render + merge with cover, TOC, bookmarks
python -m apps.api.cli build https://example.com/docs/ -o book.pdf --max-pages 20
```

## HTTP API

```bash
uvicorn apps.api.main:app --reload --port 8000
```

Endpoints:

- `GET  /api/health` — liveness
- `GET  /api/preview?url=...` — title + favicon + og:image for UX
- `POST /api/convert` — starts a conversion, returns an SSE stream of progress events
- `GET  /api/files/{token}` — download the completed PDF
- `GET  /api/conversions/{token}` — one-shot status check (non-streaming fallback)

### Environment variables

| Var | Default | Purpose |
|---|---|---|
| `SITE2BOOK_DATA_DIR` | `./data` | SQLite + generated PDFs |
| `SITE2BOOK_MAX_PAGES` | `50` | Hard ceiling on pages per conversion |
| `SITE2BOOK_MAX_CONCURRENT_JOBS` | `2` | Playwright pool size |
| `SITE2BOOK_RATE_LIMIT_PER_HOUR` | `3` | Per-IP limit |
| `SITE2BOOK_FILE_TTL_HOURS` | `24` | PDF retention before cleanup |
| `SITE2BOOK_ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated CORS origins |

See [../../TODO.md](../../TODO.md) for the roadmap.
