import logging
import os

from dotenv import load_dotenv

# Repo root: src/Backend -> src -> FinancialProject
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# override=True: if OPENAI_* / PLAID_* exist in the shell as empty, still load values from .env.
load_dotenv(os.path.join(_ROOT, ".env"), override=True)
load_dotenv()

# Logging before importing routes (so Connection / deps init uses this config).
log_dir = os.path.join(_ROOT, ".logs")
os.makedirs(log_dir, exist_ok=True)
_level_name = (os.getenv("LOG_LEVEL") or "INFO").strip().upper()
_level = getattr(logging, _level_name, logging.INFO)
_log_path = os.path.join(log_dir, "debug.log")
logging.basicConfig(
    level=_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(_log_path, encoding="utf-8"),
        logging.StreamHandler(),
    ],
    force=True,
)
logging.getLogger(__name__).info("Logging to %s (and stderr).", _log_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.Endpoints import router
from auth_supabase import auth_verification_enabled
from api.dashboard_route import get_dashboard_summary
from api.linked_accounts_route import delink_account, list_linked_accounts

app = FastAPI()

# CORS_ALLOW_ORIGINS=comma list in .env (e.g. https://app.example.com). Default * for local dev only.
_cors_raw = os.getenv("CORS_ALLOW_ORIGINS", "*")
_allow_origins = [x.strip() for x in _cors_raw.split(",") if x.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)
# Registered here (not only on APIRouter) so a long-lived uvicorn reload/import cache cannot drop this path.
app.add_api_route("/dashboard/summary", get_dashboard_summary, methods=["GET"])
app.add_api_route("/linked-accounts", list_linked_accounts, methods=["GET"])
app.add_api_route("/linked-accounts/{account_id}", delink_account, methods=["DELETE"])


def _first_env(*names: str) -> str:
    """Return the first non-empty env value (supports alternate .env spellings)."""
    for name in names:
        v = (os.getenv(name) or "").strip()
        if v:
            return v
    return ""


@app.get("/config/auth-public")
def auth_public_config():
    """Tells the static dashboard whether API routes require Authorization Bearer."""
    return {"bearer_required": auth_verification_enabled()}


@app.get("/config/supabase-public")
def supabase_public_config():
    """
    URL + anon key for the browser Supabase client. Reads .env (several key names supported).
    The anon key is public by design; do not put service_role here.
    """
    return {
        "supabase_url": _first_env("SUPABASE_URL", "supabase-url"),
        "supabase_anon_key": _first_env("SUPABASE_ANON_KEY", "supabase-anon-key"),
    }


@app.get("/health")
def health():
    """Quick check that this process is the Financial Engine API."""
    return {"ok": True, "service": "financial-engine-api"}


if __name__ == "__main__":
    import uvicorn
    # PORT/HOST from .env (repo root). Default 8001: avoids macOS AirPlay on 5000; README uses port 8000 for static http.server.
    _port = int(os.getenv("PORT", "8001"))
    _host = os.getenv("HOST", "127.0.0.1")
    uvicorn.run(app, host=_host, port=_port)
