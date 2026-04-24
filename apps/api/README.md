# apps/api

FastAPI backend for Site2Book. Phase 0 ships a CLI only — no HTTP server yet.

## Setup

Run from the repository root.

```bash
python -m venv .venv
.venv\Scripts\activate              # Windows
# source .venv/bin/activate         # macOS / Linux

pip install -r apps/api/requirements.txt
playwright install chromium
```

## Run the CLI

```bash
python -m apps.api.cli convert https://example.com -o out.pdf
```

Options:

- `-o, --output` — output path (default: `out.pdf`)
- `--timeout` — per-page timeout in milliseconds (default: `15000`)

## What Phase 0 does

`renderer.render_url()` opens Chromium, emulates print media, hides common page chrome (nav, footer, cookie banners, ads, chat widgets), auto-scrolls to trigger lazy images, then emits A4 PDF bytes.

See [TODO.md](../../TODO.md) for the next phases.
