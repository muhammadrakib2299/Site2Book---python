"""Render a single URL to a clean PDF using Playwright Chromium."""

from __future__ import annotations

from dataclasses import dataclass

from playwright.async_api import Browser, async_playwright


HIDE_CSS = """
nav, header, footer,
aside, [role="banner"], [role="navigation"], [role="contentinfo"],
.sidebar, .site-header, .site-footer, .global-header, .global-footer,
.cookie, .cookie-banner, .cookies, #cookie-banner, .gdpr,
.newsletter, .subscribe-banner,
.ads, .ad, [class*="advert"], [id*="advert"],
.social-share, .share-buttons,
.chat-widget, .intercom-launcher, [class*="chat-bubble"] {
    display: none !important;
    visibility: hidden !important;
}

html, body { background: #fff !important; }

@page { margin: 18mm 14mm; }
"""


@dataclass
class RenderResult:
    url: str
    title: str
    pdf_bytes: bytes


async def _auto_scroll(page) -> None:
    """Scroll to the bottom once to trigger lazy-loaded images."""
    await page.evaluate(
        """async () => {
            await new Promise(resolve => {
                let total = 0;
                const step = 600;
                const timer = setInterval(() => {
                    window.scrollBy(0, step);
                    total += step;
                    if (total >= document.body.scrollHeight) {
                        clearInterval(timer);
                        window.scrollTo(0, 0);
                        resolve();
                    }
                }, 80);
            });
        }"""
    )


async def render_url(
    url: str,
    *,
    browser: Browser | None = None,
    timeout_ms: int = 15_000,
) -> RenderResult:
    """Render `url` to PDF bytes. Opens its own browser if none is passed."""
    owns_browser = browser is None
    pw = None
    if owns_browser:
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)

    try:
        context = await browser.new_context(
            viewport={"width": 1280, "height": 1800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36 Site2Book/0.1"
            ),
        )
        page = await context.new_page()
        await page.emulate_media(media="print")
        try:
            await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        except Exception:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

        await page.add_style_tag(content=HIDE_CSS)
        await _auto_scroll(page)
        await page.wait_for_timeout(500)

        title = (await page.title()) or url
        pdf_bytes = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "18mm", "bottom": "18mm", "left": "14mm", "right": "14mm"},
            prefer_css_page_size=True,
        )

        await context.close()
        return RenderResult(url=url, title=title, pdf_bytes=pdf_bytes)
    finally:
        if owns_browser:
            await browser.close()
            if pw is not None:
                await pw.stop()
