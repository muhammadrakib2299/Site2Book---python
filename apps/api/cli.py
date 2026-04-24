"""Site2Book CLI — Phase 0: single URL to PDF.

Usage:
    python -m apps.api.cli convert <url> -o out.pdf
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from .crawler import CrawlOptions, crawl
from .renderer import render_url


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="site2book", description="Site2Book CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    convert = sub.add_parser("convert", help="Render a single URL to PDF")
    convert.add_argument("url", help="URL to render")
    convert.add_argument(
        "-o",
        "--output",
        default="out.pdf",
        help="Output PDF path (default: out.pdf)",
    )
    convert.add_argument(
        "--timeout",
        type=int,
        default=15_000,
        help="Per-page timeout in milliseconds (default: 15000)",
    )

    crawl_cmd = sub.add_parser("crawl", help="Crawl a site and print ordered page list")
    crawl_cmd.add_argument("url", help="Seed URL")
    crawl_cmd.add_argument("--max-pages", type=int, default=20)
    crawl_cmd.add_argument("--max-depth", type=int, default=5)
    crawl_cmd.add_argument("--include-subdomains", action="store_true")
    crawl_cmd.add_argument("--no-robots", action="store_true", help="Skip robots.txt checks")

    return parser.parse_args(argv)


async def _cmd_convert(url: str, output: str, timeout_ms: int) -> int:
    print(f"Rendering {url} ...")
    result = await render_url(url, timeout_ms=timeout_ms)
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(result.pdf_bytes)
    size_kb = len(result.pdf_bytes) / 1024
    print(f"Saved: {out_path}  ({size_kb:.1f} KB)")
    print(f"Title: {result.title}")
    return 0


async def _cmd_crawl(
    url: str,
    max_pages: int,
    max_depth: int,
    include_subdomains: bool,
    no_robots: bool,
) -> int:
    opts = CrawlOptions(
        max_pages=max_pages,
        max_depth=max_depth,
        include_subdomains=include_subdomains,
        respect_robots=not no_robots,
    )
    print(f"Crawling {url} (max_pages={max_pages}, depth={max_depth}) ...")
    result = await crawl(url, opts)
    print(
        f"\nFound {len(result.pages)} pages  "
        f"(skipped={result.skipped}, robots_blocked={result.robots_blocked})\n"
    )
    for i, page in enumerate(result.pages, 1):
        title = page.title[:58] + ".." if len(page.title) > 60 else page.title
        print(f"  {i:3d}. [d{page.depth}] {title:60s}  {page.url}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args.command == "convert":
        return asyncio.run(_cmd_convert(args.url, args.output, args.timeout))
    if args.command == "crawl":
        return asyncio.run(
            _cmd_crawl(
                args.url,
                args.max_pages,
                args.max_depth,
                args.include_subdomains,
                args.no_robots,
            )
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
