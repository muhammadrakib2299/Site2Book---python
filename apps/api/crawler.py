"""Crawl a website starting from a seed URL, producing an ordered list of pages.

Rules (all enforced):
- Same origin only (scheme + host). Optional include_subdomains toggle.
- Path-prefix scoping: links must start with the seed URL's path.
- Respect robots.txt (user-agent "Site2Book").
- Canonical URL dedupe: strip utm_*, fragments, trailing slashes; lowercase host.
- Skip pattern list: login, signup, search, archive pagination, print-view dupes.
- Hard caps: max_pages, max_depth, max_total_bytes.
- Prefer <nav> / role="navigation" link order when present.
"""

from __future__ import annotations

import asyncio
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Callable
from urllib import robotparser
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode

import httpx
from bs4 import BeautifulSoup


CrawlProgressFn = Callable[[str, dict], None]


USER_AGENT = "Site2Book/0.1 (+https://github.com/muhammadrakib2299/Site2Book---python)"

SKIP_PATH_PATTERNS = [
    re.compile(r"/login/?$", re.I),
    re.compile(r"/signin/?$", re.I),
    re.compile(r"/signup/?$", re.I),
    re.compile(r"/register/?$", re.I),
    re.compile(r"/logout/?$", re.I),
    re.compile(r"/search/?$", re.I),
    re.compile(r"/cart/?$", re.I),
    re.compile(r"/checkout/?$", re.I),
    re.compile(r"/wp-admin/", re.I),
    re.compile(r"/tag/", re.I),
    re.compile(r"/tags/", re.I),
    re.compile(r"/category/", re.I),
    re.compile(r"/author/", re.I),
    re.compile(r"/feed/?$", re.I),
    re.compile(r"\.(?:jpg|jpeg|png|gif|webp|svg|ico|css|js|zip|pdf|mp4|mp3|xml|rss)$", re.I),
]

SKIP_QUERY_PATTERNS = [
    re.compile(r"(^|&)print=", re.I),
    re.compile(r"(^|&)replytocom=", re.I),
    re.compile(r"(^|&)share=", re.I),
]

PAYWALL_SELECTORS = [
    ".paywall",
    ".subscription-required",
    ".subscriber-only",
    "[data-paywall]",
]


@dataclass
class CrawlOptions:
    max_pages: int = 20
    max_depth: int = 5
    max_total_bytes: int = 50 * 1024 * 1024  # 50 MB of HTML
    include_subdomains: bool = False
    path_prefix_scope: bool = True
    respect_robots: bool = True
    request_timeout_s: float = 15.0


@dataclass
class CrawlPage:
    url: str
    title: str
    depth: int


@dataclass
class CrawlResult:
    pages: list[CrawlPage] = field(default_factory=list)
    skipped: int = 0
    robots_blocked: int = 0


def canonicalize(url: str) -> str:
    """Normalize URL for dedupe: lowercase host, strip fragment, strip tracking params, drop trailing slash."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    host = host.lower()
    port = f":{parsed.port}" if parsed.port and not _is_default_port(parsed.scheme, parsed.port) else ""
    netloc = f"{host}{port}"

    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=False)
        if not k.lower().startswith(("utm_", "fbclid", "gclid", "mc_", "ref"))
    ]
    query = urlencode(query_pairs)

    path = parsed.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]

    return urlunparse((parsed.scheme.lower(), netloc, path, "", query, ""))


def _is_default_port(scheme: str, port: int) -> bool:
    return (scheme == "http" and port == 80) or (scheme == "https" and port == 443)


def _in_scope(
    link: str,
    seed_host: str,
    seed_path_prefix: str,
    opts: CrawlOptions,
) -> bool:
    parsed = urlparse(link)
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False

    if opts.include_subdomains:
        if host != seed_host and not host.endswith(f".{seed_host}"):
            return False
    else:
        if host != seed_host:
            return False

    if opts.path_prefix_scope and seed_path_prefix:
        if not parsed.path.startswith(seed_path_prefix):
            return False
    return True


def _should_skip(url: str) -> bool:
    parsed = urlparse(url)
    for pat in SKIP_PATH_PATTERNS:
        if pat.search(parsed.path):
            return True
    for pat in SKIP_QUERY_PATTERNS:
        if pat.search(parsed.query):
            return True
    return False


def _seed_path_prefix(seed_url: str) -> str:
    """Return the directory prefix of the seed path (e.g. /docs/ from /docs/intro)."""
    path = urlparse(seed_url).path or "/"
    if path.endswith("/"):
        return path
    last_slash = path.rfind("/")
    return path[: last_slash + 1] if last_slash >= 0 else "/"


async def _load_robots(seed_url: str, client: httpx.AsyncClient) -> robotparser.RobotFileParser:
    parsed = urlparse(seed_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = robotparser.RobotFileParser()
    rp.set_url(robots_url)
    try:
        resp = await client.get(robots_url, timeout=5.0)
        if resp.status_code == 200:
            rp.parse(resp.text.splitlines())
        else:
            rp.parse([])
    except Exception:
        rp.parse([])
    return rp


def _is_paywalled(soup: BeautifulSoup) -> bool:
    for sel in PAYWALL_SELECTORS:
        if soup.select_one(sel):
            return True
    return False


def _extract_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Extract links, preferring nav/sidebar order when present."""
    nav_links: list[str] = []
    for nav in soup.select('nav, [role="navigation"], aside, .sidebar, .toc'):
        for a in nav.find_all("a", href=True):
            nav_links.append(urljoin(base_url, a["href"]))

    body_links: list[str] = []
    for a in soup.find_all("a", href=True):
        body_links.append(urljoin(base_url, a["href"]))

    seen: set[str] = set()
    ordered: list[str] = []
    for link in nav_links + body_links:
        key = canonicalize(link)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(link)
    return ordered


def _extract_title(soup: BeautifulSoup, fallback: str) -> str:
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return fallback


async def crawl(
    seed_url: str,
    opts: CrawlOptions | None = None,
    *,
    on_progress: CrawlProgressFn | None = None,
    concurrency: int = 6,
) -> CrawlResult:
    opts = opts or CrawlOptions()
    emit = on_progress or (lambda _e, _d: None)
    parsed_seed = urlparse(seed_url)
    seed_host = (parsed_seed.hostname or "").lower()
    seed_prefix = _seed_path_prefix(seed_url)
    seed_canonical = canonicalize(seed_url)

    result = CrawlResult()
    seen: set[str] = {seed_canonical}
    queue: deque[tuple[str, int]] = deque([(seed_url, 0)])
    total_bytes = 0
    sem = asyncio.Semaphore(concurrency)

    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=True,
        timeout=opts.request_timeout_s,
        limits=httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency),
    ) as client:
        rp: robotparser.RobotFileParser | None = None
        if opts.respect_robots:
            rp = await _load_robots(seed_url, client)

        async def fetch_one(url: str, depth: int):
            if opts.respect_robots and rp is not None and not rp.can_fetch(USER_AGENT, url):
                return "robots", url, depth, None, []
            if _should_skip(url):
                return "skip", url, depth, None, []
            try:
                async with sem:
                    resp = await client.get(url)
            except Exception:
                return "skip", url, depth, None, []
            if resp.status_code >= 400:
                return "skip", url, depth, None, []
            ctype = resp.headers.get("content-type", "")
            if "html" not in ctype.lower():
                return "skip", url, depth, None, []
            body = resp.text
            soup = BeautifulSoup(body, "html.parser")
            if _is_paywalled(soup):
                return "skip", url, depth, None, []
            final_url = str(resp.url)
            title = _extract_title(soup, fallback=final_url)
            page = CrawlPage(url=final_url, title=title, depth=depth)
            links = _extract_links(soup, final_url) if depth < opts.max_depth else []
            return "ok", url, depth, page, (links, len(body.encode("utf-8", errors="ignore")))

        while queue and len(result.pages) < opts.max_pages:
            remaining = opts.max_pages - len(result.pages)
            batch_size = min(len(queue), remaining, concurrency)
            batch = [queue.popleft() for _ in range(batch_size)]

            tasks = [fetch_one(url, depth) for url, depth in batch]
            for coro in asyncio.as_completed(tasks):
                status, _url, depth, page, extra = await coro
                if status == "robots":
                    result.robots_blocked += 1
                    continue
                if status == "skip" or page is None:
                    result.skipped += 1
                    continue
                result.pages.append(page)
                emit("crawling", {"url": page.url, "found": len(result.pages)})
                if len(result.pages) >= opts.max_pages:
                    break
                links, size = extra
                total_bytes += size
                if total_bytes > opts.max_total_bytes:
                    queue.clear()
                    break
                for link in links:
                    if not _in_scope(link, seed_host, seed_prefix, opts):
                        continue
                    key = canonicalize(link)
                    if key in seen:
                        continue
                    seen.add(key)
                    queue.append((link, depth + 1))

    return result


async def crawl_main(seed_url: str, max_pages: int, include_subdomains: bool) -> int:
    opts = CrawlOptions(max_pages=max_pages, include_subdomains=include_subdomains)
    result = await crawl(seed_url, opts)
    print(f"Found {len(result.pages)} pages (skipped={result.skipped}, robots_blocked={result.robots_blocked})")
    for i, page in enumerate(result.pages, 1):
        print(f"  {i:3d}. [{page.depth}] {page.title[:60]:60s}  {page.url}")
    return 0


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    asyncio.run(crawl_main(url, max_pages=20, include_subdomains=False))
