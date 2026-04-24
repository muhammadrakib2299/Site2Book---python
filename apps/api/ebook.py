"""Assemble a crawl + render pipeline into one eBook PDF.

Produces a single PDF with:
- Cover page (title, source URL, date, page count)
- Table of contents (one line per chapter)
- Each chapter rendered from its source URL
- Clickable bookmarks (PDF outline) per chapter
"""

from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from playwright.async_api import async_playwright
from pypdf import PdfReader, PdfWriter

from .crawler import CrawlOptions, CrawlPage, crawl
from .renderer import render_url


ProgressFn = Callable[[str, dict], None]


@dataclass
class BuildResult:
    pdf_bytes: bytes
    page_count: int
    chapter_count: int
    title: str


def _cover_html(title: str, source_url: str, page_count: int) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{_escape(title)}</title>
<style>
  @page {{ margin: 24mm; size: A4; }}
  html, body {{ margin: 0; padding: 0; font-family: -apple-system, Segoe UI, Roboto, sans-serif; color: #111; }}
  .wrap {{ height: 100vh; display: flex; flex-direction: column; justify-content: center; text-align: center; padding: 0 24mm; }}
  h1 {{ font-size: 36pt; margin: 0 0 24pt; line-height: 1.15; }}
  .source {{ font-size: 12pt; color: #444; word-break: break-all; margin-bottom: 48pt; }}
  .meta {{ font-size: 11pt; color: #666; }}
  .brand {{ margin-top: 48pt; font-size: 10pt; letter-spacing: 2pt; text-transform: uppercase; color: #888; }}
</style></head>
<body><div class="wrap">
  <div class="brand">Site2Book</div>
  <h1>{_escape(title)}</h1>
  <div class="source">{_escape(source_url)}</div>
  <div class="meta">{page_count} pages &middot; generated {today}</div>
</div></body></html>"""


def _toc_html(title: str, chapters: list[tuple[str, int]]) -> str:
    rows = "".join(
        f'<li><span class="t">{_escape(ch)}</span><span class="dots"></span><span class="p">{pg}</span></li>'
        for ch, pg in chapters
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Contents</title>
<style>
  @page {{ margin: 22mm; size: A4; }}
  html, body {{ margin: 0; padding: 0; font-family: -apple-system, Segoe UI, Roboto, sans-serif; color: #111; }}
  h1 {{ font-size: 24pt; margin: 0 0 24pt; }}
  ol {{ list-style: none; margin: 0; padding: 0; font-size: 11pt; }}
  li {{ display: flex; align-items: baseline; padding: 6pt 0; border-bottom: 1px dotted #ddd; }}
  .t {{ flex: 0 1 auto; }}
  .dots {{ flex: 1; border-bottom: 1px dotted #bbb; margin: 0 6pt; transform: translateY(-3pt); }}
  .p {{ flex: 0 0 auto; color: #555; font-variant-numeric: tabular-nums; }}
</style></head>
<body>
  <h1>Contents</h1>
  <ol>{rows}</ol>
</body></html>"""


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


async def _render_html_to_pdf(browser, html: str) -> bytes:
    context = await browser.new_context()
    page = await context.new_page()
    await page.emulate_media(media="print")
    await page.set_content(html, wait_until="load")
    pdf = await page.pdf(format="A4", print_background=True, prefer_css_page_size=True)
    await context.close()
    return pdf


def _count_pages(pdf_bytes: bytes) -> int:
    return len(PdfReader(io.BytesIO(pdf_bytes)).pages)


def _merge_with_bookmarks(
    cover: bytes,
    toc: bytes,
    chapters: list[tuple[str, bytes]],
) -> bytes:
    writer = PdfWriter()

    for src_bytes in (cover, toc):
        for p in PdfReader(io.BytesIO(src_bytes)).pages:
            writer.add_page(p)

    chapter_starts: list[tuple[str, int]] = []
    for title, pdf_bytes in chapters:
        start_index = len(writer.pages)
        for p in PdfReader(io.BytesIO(pdf_bytes)).pages:
            writer.add_page(p)
        chapter_starts.append((title, start_index))

    writer.add_outline_item("Cover", 0)
    writer.add_outline_item("Contents", _count_pages(cover))
    for title, idx in chapter_starts:
        writer.add_outline_item(title[:80], idx)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


async def build_ebook(
    seed_url: str,
    crawl_opts: CrawlOptions | None = None,
    *,
    title: str | None = None,
    on_progress: ProgressFn | None = None,
) -> BuildResult:
    crawl_opts = crawl_opts or CrawlOptions()
    emit = on_progress or (lambda _event, _data: None)

    emit("crawling", {"url": seed_url, "found": 0})

    # Launch Chromium in parallel with the crawl — the browser cold start
    # is 2–8s and the crawl usually takes longer, so by the time we're
    # ready to render the browser is already warm.
    pw = await async_playwright().start()
    browser_task = asyncio.create_task(pw.chromium.launch(headless=True))

    try:
        crawled = await crawl(seed_url, crawl_opts, on_progress=emit)
    except Exception:
        browser_task.cancel()
        await pw.stop()
        raise

    if not crawled.pages:
        browser_task.cancel()
        await pw.stop()
        raise RuntimeError("Crawler returned zero pages")

    book_title = title or crawled.pages[0].title

    browser = await browser_task
    emit("browser_ready", {})

    chapter_pdfs: list[tuple[str, bytes, int]] = []
    try:
        for i, page in enumerate(crawled.pages, 1):
            emit("rendering", {"page": i, "total": len(crawled.pages), "url": page.url})
            result = await render_url(page.url, browser=browser)
            pcount = _count_pages(result.pdf_bytes)
            chapter_pdfs.append((page.title or page.url, result.pdf_bytes, pcount))

        emit("merging", {})

        # TOC is rendered twice so the second render knows exactly how
        # long the TOC itself will be and chapter page numbers are correct.
        cover_html = _cover_html(book_title, seed_url, sum(c[2] for c in chapter_pdfs))
        cover_pdf = await _render_html_to_pdf(browser, cover_html)
        cover_pages = _count_pages(cover_pdf)

        toc_entries_preview = [(t, 0) for t, _, _ in chapter_pdfs]
        toc_pdf_preview = await _render_html_to_pdf(browser, _toc_html(book_title, toc_entries_preview))
        toc_pages = _count_pages(toc_pdf_preview)

        running = cover_pages + toc_pages + 1
        toc_entries: list[tuple[str, int]] = []
        for title_ch, _pdf, pcount in chapter_pdfs:
            toc_entries.append((title_ch, running))
            running += pcount

        toc_pdf = await _render_html_to_pdf(browser, _toc_html(book_title, toc_entries))
    finally:
        await browser.close()
        await pw.stop()

    merged = _merge_with_bookmarks(
        cover_pdf,
        toc_pdf,
        [(t, pdf) for t, pdf, _ in chapter_pdfs],
    )
    total_pages = _count_pages(merged)

    emit("done", {"pages": total_pages, "chapters": len(chapter_pdfs)})
    return BuildResult(
        pdf_bytes=merged,
        page_count=total_pages,
        chapter_count=len(chapter_pdfs),
        title=book_title,
    )


async def build_main(seed_url: str, output: str, max_pages: int) -> int:
    def _log(event: str, data: dict) -> None:
        if event == "crawling":
            print(f"[crawl] {data['url']}")
        elif event == "rendering":
            print(f"[render] {data['page']}/{data['total']}  {data['url']}")
        elif event == "merging":
            print("[merge] assembling eBook ...")
        elif event == "done":
            print(f"[done] {data['chapters']} chapters, {data['pages']} pages")

    from pathlib import Path

    result = await build_ebook(
        seed_url,
        CrawlOptions(max_pages=max_pages),
        on_progress=_log,
    )
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(result.pdf_bytes)
    print(f"\nSaved: {out_path}  ({len(result.pdf_bytes) / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    asyncio.run(build_main(url, "book.pdf", 10))
