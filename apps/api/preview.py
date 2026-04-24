"""Cheap URL preview: fetch <title>, favicon, og:image. Used for UX on the input form."""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


USER_AGENT = "Site2Book-Preview/0.1"


async def fetch_preview(url: str, timeout_s: float = 6.0) -> dict:
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=timeout_s,
        ) as client:
            resp = await client.get(url)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    if resp.status_code >= 400:
        return {"ok": False, "error": f"HTTP {resp.status_code}"}

    soup = BeautifulSoup(resp.text, "html.parser")
    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    og_image = _meta(soup, "og:image")
    description = _meta(soup, "og:description") or _meta(soup, "description")

    base = f"{urlparse(str(resp.url)).scheme}://{urlparse(str(resp.url)).netloc}"
    favicon = _find_icon(soup, base) or urljoin(base, "/favicon.ico")

    return {
        "ok": True,
        "url": str(resp.url),
        "title": title,
        "description": description,
        "favicon": favicon,
        "og_image": og_image,
    }


def _meta(soup: BeautifulSoup, key: str) -> str | None:
    tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


def _find_icon(soup: BeautifulSoup, base: str) -> str | None:
    for rel in ("icon", "shortcut icon", "apple-touch-icon"):
        tag = soup.find("link", rel=lambda v: v and rel in v)
        if tag and tag.get("href"):
            return urljoin(base, tag["href"])
    return None
