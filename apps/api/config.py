"""Runtime configuration via environment variables with sensible defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    db_path: Path
    files_dir: Path
    max_pages: int
    max_concurrent_jobs: int
    rate_limit_per_hour: int
    file_ttl_hours: int
    allowed_origins: tuple[str, ...]


def load_settings() -> Settings:
    data_dir = Path(os.getenv("SITE2BOOK_DATA_DIR", "./data")).resolve()
    files_dir = data_dir / "files"
    data_dir.mkdir(parents=True, exist_ok=True)
    files_dir.mkdir(parents=True, exist_ok=True)

    origins = os.getenv("SITE2BOOK_ALLOWED_ORIGINS", "http://localhost:3000")
    return Settings(
        data_dir=data_dir,
        db_path=data_dir / "site2book.db",
        files_dir=files_dir,
        max_pages=_env_int("SITE2BOOK_MAX_PAGES", 50),
        max_concurrent_jobs=_env_int("SITE2BOOK_MAX_CONCURRENT_JOBS", 2),
        rate_limit_per_hour=_env_int("SITE2BOOK_RATE_LIMIT_PER_HOUR", 3),
        file_ttl_hours=_env_int("SITE2BOOK_FILE_TTL_HOURS", 24),
        allowed_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
    )


settings = load_settings()
