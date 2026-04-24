"""SQLite storage for conversion records, via SQLModel."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select

from .config import settings


class Conversion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True, unique=True)
    url: str
    title: Optional[str] = None
    status: str = Field(default="queued")  # queued | running | completed | failed
    error: Optional[str] = None
    page_count: Optional[int] = None
    size_bytes: Optional[int] = None
    file_path: Optional[str] = None
    client_ip: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


_engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    SQLModel.metadata.create_all(_engine)


def session() -> Session:
    return Session(_engine)


def count_recent_for_ip(ip: str, since: datetime) -> int:
    with session() as s:
        stmt = select(Conversion).where(
            Conversion.client_ip == ip,
            Conversion.created_at >= since,
        )
        return len(s.exec(stmt).all())


def get_by_token(token: str) -> Optional[Conversion]:
    with session() as s:
        stmt = select(Conversion).where(Conversion.token == token)
        return s.exec(stmt).first()


def create_conversion(token: str, url: str, client_ip: str) -> Conversion:
    with session() as s:
        row = Conversion(token=token, url=url, client_ip=client_ip, status="queued")
        s.add(row)
        s.commit()
        s.refresh(row)
        return row


def update_conversion(token: str, **fields) -> None:
    with session() as s:
        stmt = select(Conversion).where(Conversion.token == token)
        row = s.exec(stmt).first()
        if row is None:
            return
        for k, v in fields.items():
            setattr(row, k, v)
        s.add(row)
        s.commit()


def list_expired(before: datetime) -> list[Conversion]:
    with session() as s:
        stmt = select(Conversion).where(Conversion.created_at < before)
        return list(s.exec(stmt).all())


def delete_conversion(token: str) -> None:
    with session() as s:
        stmt = select(Conversion).where(Conversion.token == token)
        row = s.exec(stmt).first()
        if row:
            s.delete(row)
            s.commit()
