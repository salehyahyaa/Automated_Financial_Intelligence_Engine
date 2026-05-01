# Automated Financial Intelligence Engine

Backend service that ingests financial data through **Plaid**, stores it in **Postgres**, and exposes analytics plus an **LLM-powered** assistant. Optional **Supabase Auth** ties Plaid items and data to signed-in users.

The stack is **in production** (for example on **AWS EC2** with systemd); see [documentation/DEPLOY.md](documentation/DEPLOY.md) and the [deploy/](deploy/) scripts. API routes are summarized in [documentation/API_ENDPOINTS.md](documentation/API_ENDPOINTS.md).

## Features

- Secure Plaid Link OAuth flow and token exchange  
- Account and transaction sync (checking, credit, cursor-based transactions)  
- Statistical and predictive analytics modules  
- Natural-language Q&A over your finance context (`/chat`, `/chat/stream`)  
- Dashboard JSON and linked-account management  

## Project structure

```
FinancialProject/
├─ .env.example
├─ .gitignore
├─ LICENSE
├─ README.md
├─ requirements.txt
├─ deploy/
│  ├─ ec2-bootstrap.sh
│  └─ financial-engine-api.service.template
├─ db_architecture/
│  ├─ schema_v1.sql
│  ├─ schema_v2.sql
│  ├─ schema_financialengine_supabase.sql
│  └─ migration_v2_user_cursor_removed.sql
├─ documentation/
│  ├─ DEPLOY.md
│  └─ API_ENDPOINTS.md
├─ src/
│  ├─ Backend/
│  │  ├─ main.py
│  │  ├─ deps.py
│  │  ├─ auth_supabase.py
│  │  ├─ gunicorn_start.sh
│  │  ├─ Accounts.py
│  │  ├─ CheckingAccounts.py
│  │  ├─ CreditCards.py
│  │  ├─ DataAutomation.py
│  │  ├─ PlaidConnector.py
│  │  ├─ api/
│  │  │  ├─ __init__.py
│  │  │  ├─ Endpoints.py
│  │  │  ├─ dashboard_route.py
│  │  │  └─ linked_accounts_route.py
│  │  ├─ services/
│  │  │  ├─ __init__.py
│  │  │  └─ finance_context.py
│  │  ├─ Analytics/
│  │  ├─ LLM/
│  │  └─ database/
│  └─ Frontend/
│     ├─ index.html
│     ├─ auth/
│     │  ├─ auth-session.js
│     │  └─ auth-ui.js
│     ├─ dashboard/
│     │  ├─ dashboard.html
│     │  ├─ dashboard.js
│     │  └─ dashboard.css
│     ├─ plaid/
│     │  └─ plaid.js
│     ├─ chat/
│     │  └─ chatbox.js
│     ├─ settings/
│     │  └─ settings-ui.js
│     ├─ shared/
│     │  ├─ nav-drawer.js
│     │  └─ refresh.js
└─ tests/   (optional)
```

## Requirements

- **Python 3.11+** (matches `deploy/ec2-bootstrap.sh` and current dependency pins)  
- **PostgreSQL** (or compatible URL in `DATABASE_URL`)  
- **Plaid** developer credentials  
- **OpenAI** API key for chat (see `.env.example` for variable names)  

## Installation

### 1. Clone and enter the repo

```bash
git clone https://github.com/salehyahyaa/Automated_Financial_Intelligence_Engine.git
cd Automated_Financial_Intelligence_Engine
```

(Your local folder may be named `FinancialProject`; the path only needs to match where you run commands from.)

### 2. Virtual environment

From the **repository root** (recommended; matches production bootstrap):

```bash
python3.12 -m venv .venv   # or python3.11 / python3 if >= 3.11
source .venv/bin/activate    # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment file

```bash
cp .env.example .env
```

Edit **`.env` at the repo root** (same level as `README.md`). The API loads that file automatically.

**Minimum to run meaningfully:**

| Area | Variables (see `.env.example`) |
|------|--------------------------------|
| Database | `DATABASE_URL` (or supported alternates in the example file) |
| Plaid | `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ENV` |
| Chat | `OPENAI_API_KEY` or `OPEN_AI_API_KEY` |
| Production listen | `HOST`, `PORT`; set `CORS_ALLOW_ORIGINS` to your real frontend origin(s) |

Optional: **Supabase** keys and JWT settings for auth and row-level user binding.

### 4. Database schema

Apply the SQL appropriate to your environment from **`db_architecture/`** (for example `schema_financialengine_supabase.sql` on Supabase Postgres). Without a migrated DB, sync and chat endpoints will fail or return empty structured responses.

## How to run

### Backend (development)

```bash
cd src/Backend
python main.py
```

Defaults: **`http://127.0.0.1:8001`** (`HOST` / `PORT` in `.env` override). Avoid port **5000** on macOS (AirPlay).

**Same process also serves the UI** at **`/app/`**; opening **`http://127.0.0.1:8001/`** redirects to the dashboard. Interactive API docs: **`/docs`**.

### Backend (production)

Use **Gunicorn + Uvicorn workers** or the provided **systemd** unit (after `./deploy/ec2-bootstrap.sh`). Full steps: **[documentation/DEPLOY.md](documentation/DEPLOY.md)**.

```bash
chmod +x src/Backend/gunicorn_start.sh
./src/Backend/gunicorn_start.sh
```

### Frontend only (optional local static server)

If you want the UI on a **different port** than the API (e.g. `python3 -m http.server 8000` under `src/Frontend`), set the dashboard **`<meta name="api-base" content="http://127.0.0.1:8001" />`** to your API origin and allow that origin in **`CORS_ALLOW_ORIGINS`**.

- Demo Plaid page: `http://127.0.0.1:8000/index.html`  
- Dashboard path on the static server: `http://127.0.0.1:8000/dashboard/dashboard.html`  

## Documentation

| File | Content |
|------|---------|
| [documentation/API_ENDPOINTS.md](documentation/API_ENDPOINTS.md) | Short description of each HTTP route |
| [documentation/DEPLOY.md](documentation/DEPLOY.md) | Production ports, env, Gunicorn, CORS, static `/app` behavior |
| [deploy/ec2-bootstrap.sh](deploy/ec2-bootstrap.sh) | EC2 venv + systemd unit generation |

## What to expect

After the API and database are configured, you can link a bank via Plaid, sync accounts and transactions, open the dashboard for balances and activity, and use the chat panel for natural-language questions grounded on your stored finance context.
