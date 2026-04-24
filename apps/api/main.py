"""FastAPI entry point: SSE-streaming conversions, file downloads, URL previews."""

from __future__ import annotations

import asyncio
import json
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, HttpUrl
from sse_starlette.sse import EventSourceResponse

from . import cleanup, db, rate_limit, storage
from .config import settings
from .crawler import CrawlOptions
from .ebook import build_ebook
from .preview import fetch_preview


_job_semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    cleanup.run_once()
    task = asyncio.create_task(cleanup.run_periodic())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="Site2Book API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ConvertRequest(BaseModel):
    url: HttpUrl
    max_pages: int = Field(default=20, ge=1, le=200)
    include_subdomains: bool = False
    title: str | None = None


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/preview")
async def preview(url: str = Query(..., min_length=8)) -> dict:
    return await fetch_preview(url)


@app.post("/api/convert")
async def convert(req: ConvertRequest, request: Request):
    client_ip = request.client.host if request.client else ""
    allowed, count = rate_limit.is_allowed(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit reached ({count}/{settings.rate_limit_per_hour} per hour)",
        )

    if req.max_pages > settings.max_pages:
        raise HTTPException(
            status_code=400,
            detail=f"max_pages exceeds server cap of {settings.max_pages}",
        )

    token = secrets.token_urlsafe(16)
    db.create_conversion(token=token, url=str(req.url), client_ip=client_ip)

    opts = CrawlOptions(
        max_pages=req.max_pages,
        include_subdomains=req.include_subdomains,
    )

    queue: asyncio.Queue[dict] = asyncio.Queue()

    def emit(event: str, data: dict) -> None:
        queue.put_nowait({"event": event, **data})

    async def run_job() -> None:
        async with _job_semaphore:
            db.update_conversion(token, status="running")
            try:
                result = await build_ebook(
                    str(req.url),
                    opts,
                    title=req.title,
                    on_progress=emit,
                )
                path = storage.save_pdf(token, result.pdf_bytes)
                db.update_conversion(
                    token,
                    status="completed",
                    title=result.title,
                    page_count=result.page_count,
                    size_bytes=len(result.pdf_bytes),
                    file_path=str(path),
                    completed_at=datetime.now(timezone.utc),
                )
                queue.put_nowait(
                    {
                        "event": "done",
                        "token": token,
                        "download_url": f"/api/files/{token}",
                        "pages": result.page_count,
                        "size_bytes": len(result.pdf_bytes),
                        "title": result.title,
                    }
                )
            except Exception as exc:
                db.update_conversion(token, status="failed", error=str(exc))
                queue.put_nowait({"event": "error", "message": str(exc)})
            finally:
                queue.put_nowait({"event": "__end__"})

    task = asyncio.create_task(run_job())

    async def event_gen():
        try:
            while True:
                item = await queue.get()
                if item.get("event") == "__end__":
                    return
                yield {"event": "message", "data": json.dumps(item)}
        finally:
            if not task.done():
                # Client disconnected — let the job keep running so the
                # PDF is still available via /api/files/{token} afterwards.
                pass

    return EventSourceResponse(event_gen())


@app.get("/api/files/{token}")
async def download(token: str):
    row = db.get_by_token(token)
    if row is None or row.status != "completed":
        raise HTTPException(status_code=404, detail="Not found")
    path = storage.open_pdf(token)
    if path is None:
        raise HTTPException(status_code=410, detail="File expired")
    filename = _safe_filename(row.title or "site2book") + ".pdf"
    return FileResponse(path, media_type="application/pdf", filename=filename)


@app.get("/api/conversions/{token}")
async def status(token: str) -> dict:
    row = db.get_by_token(token)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "token": row.token,
        "status": row.status,
        "url": row.url,
        "title": row.title,
        "pages": row.page_count,
        "size_bytes": row.size_bytes,
        "error": row.error,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def _safe_filename(name: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "-_ " else "_" for c in name).strip()
    return (cleaned or "site2book")[:80]
