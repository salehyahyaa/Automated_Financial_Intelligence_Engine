# API endpoints (brief)

Base URL is your API host (for example `https://api.example.com` or `http://127.0.0.1:8001`). Paths below are relative to that origin.

**Auth:** If Supabase JWT verification is enabled, protected routes expect `Authorization: Bearer <access_token>`. Call **`GET /config/auth-public`** to see whether the API requires a bearer token.

---

## App shell & static UI

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/` | Redirects to `/app/dashboard/dashboard.html` (single-host deploy). |
| `GET` | `/app/...` | Static files from `src/Frontend` (dashboard, JS, CSS). Not JSON APIs. |

---

## Health & configuration

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness check. Returns `{ "ok": true, "service": "financial-engine-api" }`. |
| `GET` | `/config/auth-public` | Whether the API expects `Authorization: Bearer` on protected routes (`bearer_required`). |
| `GET` | `/config/supabase-public` | Public Supabase URL and anon key for the browser client (from server env). |

---

## Plaid linking & sync

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/create_link_token` | Creates a Plaid Link token for the browser; optional `client_user_id` from auth. |
| `POST` | `/exchange_public_token` | Body: `{ "public_token": "..." }`. Exchanges the public token, stores Plaid item + access token in DB. |
| `POST` | `/sync_checking_accounts` | Pulls depository accounts from the user’s latest linked Plaid item and stores them. |
| `POST` | `/sync_credit_accounts` | Pulls credit accounts from the latest linked item and stores them. |
| `POST` | `/sync-transactions` | Body (optional): date range / cursor fields. Fetches transactions from Plaid, normalizes them, upserts into DB, updates sync cursor. |
| `POST` | `/refresh_account_data` | Runs checking sync, credit sync, and a full transaction sync in one call. |

---

## Dashboard & linked accounts

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/dashboard/summary` | JSON snapshot for the dashboard: linked state, accounts, recent transactions, finance context (no LLM). |
| `GET` | `/linked-accounts` | Lists Plaid-linked accounts for the current user (settings / delink UI). |
| `DELETE` | `/linked-accounts/{account_id}` | Removes the Plaid **item** that owns that account row (cascades local data); calls Plaid `item_remove` when possible. |

---

## Assistant (LLM)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/chat` | Body: `{ "message": "..." }` (or `content`). Non-streaming reply using finance context + OpenAI. |
| `POST` | `/chat/stream` | Same body as `/chat`; returns **SSE** (`text/event-stream`) with JSON lines: `start`, `delta` (token chunks), `done`, or `error`. |

---

## Interactive docs

When the server is running, OpenAPI UI is at **`/docs`** (Swagger) and **`/redoc`**.
