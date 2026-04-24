# Backend container: FastAPI + Playwright Chromium.
#
# Use Microsoft's official Playwright image so the browser binaries and
# every matching OS library (libnss, libatk, fonts, etc.) are already
# correct for the Playwright version we pin.

FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SITE2BOOK_DATA_DIR=/data

WORKDIR /app

COPY apps/api/requirements.txt /app/apps/api/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/apps/api/requirements.txt

COPY apps/__init__.py /app/apps/__init__.py
COPY apps/api /app/apps/api

RUN mkdir -p /data/files

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
import os; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
