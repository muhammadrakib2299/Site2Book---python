"""Delete expired conversions + files. Run at startup and hourly."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from . import db, storage
from .config import settings


def run_once() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.file_ttl_hours)
    removed = 0
    for row in db.list_expired(cutoff):
        storage.delete_pdf(row.token)
        db.delete_conversion(row.token)
        removed += 1
    return removed


async def run_periodic(interval_s: int = 3600) -> None:
    while True:
        try:
            run_once()
        except Exception:
            pass
        await asyncio.sleep(interval_s)
