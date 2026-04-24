# Site2Book — Build Plan

Phased plan. Each phase produces something testable on its own. Don't start the next phase until the current one's "done when" bar is met.

---

## Phase 0 — Single URL → PDF (CLI only)

**Goal**: prove Playwright produces clean PDFs from real sites. No API, no UI.

- [ ] Create `apps/api/` with `requirements.txt` (fastapi, playwright, pypdf, sqlmodel, pydantic)
- [ ] Write `renderer.py` — function that takes a URL and returns PDF bytes
- [ ] Use Chromium `page.pdf()` with `print` media emulation
- [ ] Inject CSS to hide `nav, header, footer, .sidebar, .cookie-banner, [role="banner"], [role="navigation"]`
- [ ] Wait for `networkidle` with 15s timeout, then 500ms settle
- [ ] Auto-scroll to bottom once to trigger lazy-loaded images
- [ ] Build a CLI: `python -m apps.api.cli convert <url> -o out.pdf`
- [ ] Test against 5 very different sites (blog post, docs site, news article, SPA, long-form article)

**Done when**: single-page PDF output looks clean on all 5 test sites.

---

## Phase 1 — Crawler

**Goal**: turn one URL into an ordered list of URLs worth converting.

- [ ] Write `crawler.py` with same-origin rule (scheme + host)
- [ ] Add path-prefix scoping (links must start with the input URL's path)
- [ ] Fetch and respect `robots.txt` (user-agent, disallow, crawl-delay)
- [ ] Canonical URL dedupe: strip `utm_*`, fragments, trailing slashes; lowercase host
- [ ] Skip pattern list: `/login`, `/signup`, `/search`, `?print=`, tag/archive pagination
- [ ] BFS traversal with hard caps: `max_pages`, `max_depth`, `max_total_bytes`
- [ ] Prefer nav/sidebar link order when `<nav>` or `role="navigation"` exists
- [ ] Detect paywall/login walls and skip (check for common selectors + status codes)
- [ ] CLI: `python -m apps.api.cli crawl <url> --max-pages 20` → prints ordered list

**Done when**: crawling a docs site produces URLs in a sensible reading order, with no duplicates and no junk pages.

---

## Phase 2 — eBook assembly (cover + TOC + merge)

**Goal**: the output is an eBook, not a stapled stack of PDFs.

- [ ] Write `ebook.py`
- [ ] Cover page: source URL, date, page count, favicon
- [ ] TOC page: list of chapters with page numbers
- [ ] Use pypdf `add_outline_item` to add clickable bookmarks per page
- [ ] Inject `<h1>` with page title if missing (helps TOC anchoring)
- [ ] Merge order matches crawler's ordered list
- [ ] CLI: `python -m apps.api.cli build <url> --max-pages 20 -o book.pdf` (end-to-end)
- [ ] Test on 3 sites and open the output in Adobe Reader + browser PDF viewer

**Done when**: the output has a cover, a working TOC, clickable bookmarks, and reads like a book.

---

## Phase 3 — FastAPI with SSE streaming

**Goal**: wrap the CLI pipeline in an HTTP API with real-time progress.

- [ ] `db.py` — SQLite via SQLModel, single `conversions` table (id, url, status, created_at, file_path, error)
- [ ] `storage.py` — local filesystem for now, behind an interface we can swap for S3 later
- [ ] `POST /api/convert` — accepts URL + options, returns SSE stream
- [ ] Stream events: `crawling`, `rendering` (with page N of total), `merging`, `done`, `error`
- [ ] `GET /api/files/{token}` — signed token, 24h expiry, returns PDF
- [ ] `GET /api/preview?url=` — returns `{title, favicon, og_image}` for UX
- [ ] Playwright browser pool (max 2–3 instances, reuse contexts)
- [ ] Per-IP rate limit: 3 conversions/hour
- [ ] Request size guards: max 50 pages, max 15s per page render
- [ ] Cleanup job: delete files older than 24h on startup + hourly

**Done when**: `curl -N` against `/api/convert` streams progress and ends with a working download link.

---

## Phase 4 — Next.js frontend

**Goal**: polished web UI a non-technical user can use.

- [ ] `npx create-next-app@latest` with TypeScript, Tailwind, App Router
- [ ] Install shadcn/ui
- [ ] `app/page.tsx` — URL input, max-pages dropdown, "Generate eBook" button
- [ ] Optional preview card showing favicon + title (calls `/api/preview`)
- [ ] `app/convert/page.tsx` — SSE client showing live progress bar + current URL
- [ ] `lib/sse.ts` — typed SSE client
- [ ] Download button appears on `done` event
- [ ] Error states: invalid URL, robots.txt blocks, all pages failed, rate limit hit
- [ ] Empty, loading, success, and error screens all present
- [ ] Test in Chrome + Firefox + Safari

**Done when**: a user can paste a URL and get a downloaded PDF without touching the CLI or reading any logs.

---

## Phase 5 — Deploy

**Goal**: public URL, stays up.

- [ ] `docker/Dockerfile` based on `mcr.microsoft.com/playwright:v1.x-jammy`
- [ ] `compose.yml` for local dev parity
- [ ] Deploy to Fly.io (or Railway) — single container, 2 GB RAM minimum
- [ ] Wire custom domain + TLS
- [ ] Persistent volume for SQLite + output files
- [ ] Health check endpoint `/api/health`
- [ ] Basic logging (structured, JSON)
- [ ] Error reporting (Sentry free tier)

**Done when**: the tool is publicly reachable at a domain and survives a container restart.

---

## Phase 6 — Polish

**Goal**: things that make users keep coming back.

- [ ] "Email me the PDF" option (SES or Resend)
- [ ] Retry failed pages once before giving up
- [ ] Better paywall detection (Readability score threshold)
- [ ] Remember last 5 conversions in localStorage
- [ ] OG image for social sharing
- [ ] Analytics (privacy-friendly — Plausible or similar)
- [ ] "Report a broken site" link

---

## Later (post-MVP)

- [ ] User accounts + history
- [ ] EPUB export (`ebooklib`)
- [ ] AI summary per chapter
- [ ] Scheduled re-crawls (weekly snapshot of a docs site)
- [ ] S3 storage (swap `storage.py` implementation)
- [ ] Free vs paid tier (watermark, page limits, auth)
- [ ] Custom cover page uploads
- [ ] Custom CSS injection per conversion

---

## Known pitfalls (keep in mind throughout)

- **Playwright memory** — pool of 2–3 max, reuse contexts, never spawn per page
- **SPA rendering** — `networkidle` isn't always enough; wait for a DOM signal like `h1`
- **Lazy images** — scroll to bottom once before calling `page.pdf()`
- **Infinite pages** — hard-cap depth, total pages, total bytes — all three
- **Legal** — add a "I have rights to this content" checkbox on the form
- **Abuse** — rate limit from day one, don't retrofit it
