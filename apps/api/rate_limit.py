"""Simple per-IP rate limiter backed by the SQLite conversions table.

For MVP: no Redis, no sliding-window magic. We just count how many
conversions this IP started in the last hour. If we later want richer
abuse controls, swap this module.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import db
from .config import settings


def is_allowed(client_ip: str) -> tuple[bool, int]:
    """Return (allowed, current_count_in_window)."""
    if not client_ip:
        return True, 0
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    count = db.count_recent_for_ip(client_ip, since)
    return count < settings.rate_limit_per_hour, count
