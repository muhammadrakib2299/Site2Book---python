"""File storage abstraction. Local filesystem for MVP — swap for S3 later.

All file access goes through `save_pdf` and `open_pdf` so we can change
the backend without touching callers.
"""

from __future__ import annotations

from pathlib import Path

from .config import settings


def path_for(token: str) -> Path:
    return settings.files_dir / f"{token}.pdf"


def save_pdf(token: str, data: bytes) -> Path:
    target = path_for(token)
    target.write_bytes(data)
    return target


def open_pdf(token: str) -> Path | None:
    target = path_for(token)
    return target if target.exists() else None


def delete_pdf(token: str) -> None:
    target = path_for(token)
    if target.exists():
        target.unlink()
