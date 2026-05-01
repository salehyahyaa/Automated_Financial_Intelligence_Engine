"""Shared app singletons (DB, Plaid, automation)."""
import os

from dotenv import load_dotenv

# Repo root is src/Backend -> parent -> parent (FinancialProject). Load .env before other imports read os.environ.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(_REPO_ROOT, ".env"), override=True)
load_dotenv()

from DataAutomation import DataAutomation
from database.Connection import Connection
from PlaidConnector import PlaidConnector

db = Connection()
dataAutomation = DataAutomation(db)
PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")
PLAID_ENV = os.getenv("PLAID_ENV")
bank = PlaidConnector(PLAID_CLIENT_ID, PLAID_SECRET, PLAID_ENV)
