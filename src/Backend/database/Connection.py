import logging
import os
import re
from urllib.parse import quote

import psycopg2
from dotenv import load_dotenv

_log = logging.getLogger(__name__)


def _normalize_postgres_uri_if_password_starts_with_at(uri: str) -> str:
    """
    Fix common mistake: postgresql://postgres:@Secret@host/... where the DB password
    literally begins with '@'. The first '@' must be percent-encoded or libpq treats
    'Secret@host' as the hostname. Already-correct URIs (postgres:%40...@host) are unchanged.
    """
    s = (uri or "").strip()
    if not s or "postgresql://" not in s.lower():
        return s
    # postgres:@<password-without-unencoded-at>@<hostpath> — password may start with @
    m = re.match(
        r"^(postgresql://postgres):(@[^@]+)@([^?\s#]+)(\?.*)?$",
        s,
        flags=re.IGNORECASE,
    )
    if not m:
        return s
    prefix, password_raw, host_path, query = m.groups()
    query = query or ""
    encoded = quote(password_raw, safe="")
    if encoded == password_raw:
        return s
    fixed = f"{prefix}:{encoded}@{host_path}{query}"
    _log.warning(
        "DATABASE_URL: password appears to start with '@' without encoding; "
        "normalized for connect (use %%40... in .env to avoid this)."
    )
    return fixed

# Repo root: database -> Backend -> src -> FinancialProject (three parents of this file's directory).
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
load_dotenv(os.path.join(_REPO_ROOT, ".env"), override=True)
load_dotenv()


def _pick_database_url():
    # Supabase / hosting often use DATABASE_URL; some templates use POSTGRES_URL or SUPABASE_DATABASE_URL.
    for key in ("DATABASE_URL", "POSTGRES_URL", "SUPABASE_DATABASE_URL"):
        raw = os.getenv(key)
        if raw and str(raw).strip():
            return (str(raw).strip(), key)
    return (None, None)


class Connection:
    # Holds a single psycopg2 connection for reuse; callers use cursor() or get_connection().

    def __init__(self):
        url, url_key = _pick_database_url()
        if url:
            url = _normalize_postgres_uri_if_password_starts_with_at(url)
        self._database_url = url
        self._database_url_key = url_key
        self.host = os.getenv("DB_HOST")
        self.port = os.getenv("DB_PORT")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.database = os.getenv("DB_NAME")
        self.connection = None
        if self._database_url:
            _log.info("Database: using %s from environment (value not logged).", url_key)
        elif self.host and self.user and self.database:
            _log.info("Database: using discrete DB_HOST/DB_USER/DB_NAME (password %s).", "set" if self.password else "empty")
        else:
            _log.warning(
                "Database env missing: no DATABASE_URL/POSTGRES_URL/SUPABASE_DATABASE_URL; "
                "discrete vars have host=%s user=%s dbname=%s (all required for fallback). "
                "Put .env in repo root: %s",
                bool(self.host),
                bool(self.user),
                bool(self.database),
                _REPO_ROOT,
            )

    def get_connection(self):
        # Open or reuse the connection; reconnect if the server closed it.
        if self.connection is None:
            try:
                self.connection = self._open_new_connection()
            except psycopg2.Error as e:
                _log.error("Postgres connection failed", exc_info=True)
                raise Exception(f"Connection to DB Failed: {e}")
        elif self.connection.closed:
            try:
                self.connection = self._open_new_connection()
            except psycopg2.Error as e:
                _log.error("Postgres reconnection failed", exc_info=True)
                raise Exception(f"Connection to DB Failed: {e}")
        return self.connection

    def _open_new_connection(self):
        # One code path for URI vs discrete params.
        if self._database_url:
            try:
                return psycopg2.connect(self._database_url)
            except psycopg2.Error as e:
                _log.error("Postgres connect via URL failed (check sslmode= require for Supabase)", exc_info=True)
                raise
        # Password may be empty for local trust auth; remote DBs still need a real password in URI or DB_PASSWORD.
        if not all([self.host, self.user, self.database]):
            msg = (
                "Database not configured: set DATABASE_URL (or POSTGRES_URL / SUPABASE_DATABASE_URL) "
                "in the repo-root .env, or set DB_HOST, DB_USER, DB_NAME (and DB_PASSWORD if required). "
                f"Resolved repo root for .env: {_REPO_ROOT}"
            )
            _log.error(msg)
            raise Exception(msg)
        port = int(self.port or 5432)
        return psycopg2.connect(
            host=self.host,
            port=port,
            user=self.user,
            password=self.password if self.password is not None else "",
            database=self.database,
        )

    def cursor(self):
        # Return a new cursor on the live connection (creates connection if needed).
        try:
            if self.connection is None or self.connection.closed:
                self.get_connection()
            return self.connection.cursor()
        except psycopg2.Error as e:
            _log.error("Failed to create cursor", exc_info=True)
            raise Exception(f"Failed to create cursor: {e}")

    def close_connection(self):
        # Close and drop reference so the next get_connection() opens a fresh socket.
        if self.connection and not self.connection.closed:
            self.connection.close()
        self.connection = None
