"""Site2Book CLI — Phase 0: single URL to PDF.

Usage:
    python -m apps.api.cli convert <url> -o out.pdf
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

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


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args.command == "convert":
        return asyncio.run(_cmd_convert(args.url, args.output, args.timeout))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
