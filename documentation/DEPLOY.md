# Running in production

## Ports

- **`PORT`** (default **8001** in `main.py` / `gunicorn_start.sh`): API listen port. Set to what Nginx proxies to (e.g. `8080` internally).
- Avoid **`5000`** on macOS (AirPlay). Keep frontend static server on a **different** port than the API if both run on one machine.

## Environment

- Repo-root **`.env`**: `DATABASE_URL`, Plaid keys, OpenAI keys, `HOST`, `PORT`, `CORS_ALLOW_ORIGINS`, etc.
- **`CORS_ALLOW_ORIGINS`**: comma-separated origins, e.g. `https://yourdomain.com` (do not use `*` in production with credentials if browsers reject it).

## Gunicorn (recommended)

From repo root after `chmod +x src/Backend/gunicorn_start.sh`:

```bash
./src/Backend/gunicorn_start.sh
```

Or manually from `src/Backend` after exporting env:

```bash
gunicorn main:app -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:8001
```

Place **Nginx** (or similar) in front for TLS and static files; point `proxy_pass` at `http://127.0.0.1:$PORT`.

## Dev (uvicorn only)

```bash
cd src/Backend
python main.py
```

Uses **`HOST`** / **`PORT`** from `.env` (defaults `127.0.0.1:8001`).

## Frontend API URL

Set `<meta name="api-base" content="https://api.yourdomain.com" />` in `dashboard/dashboard.html` / `index.html`, or set `window.API_BASE` before loading `plaid/plaid.js`.
