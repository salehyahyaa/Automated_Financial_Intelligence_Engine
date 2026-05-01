# Running in production

Route-by-route behavior is summarized in **[API_ENDPOINTS.md](API_ENDPOINTS.md)**.

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

The API serves static files at **`/app/`** (repo `src/Frontend`). Open **`http://<host>:<PORT>/`** (redirects to the dashboard) or **`http://<host>:<PORT>/app/dashboard/dashboard.html`**. When the path starts with `/app/`, the dashboard script sets **`api-base`** to **`location.origin`** so the browser talks to the same server.

For a separate static host (e.g. S3), set `<meta name="api-base" content="https://api.yourdomain.com" />` in `dashboard/dashboard.html` / `index.html`, and set **`CORS_ALLOW_ORIGINS`** to that static origin.
