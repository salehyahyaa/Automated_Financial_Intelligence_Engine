import plaid 
import os
import logging
from plaid.model.country_code import CountryCode  
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid import ApiClient, Configuration
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.products import Products
from plaid import Environment
from plaid.model.transactions_sync_request import TransactionsSyncRequest  # Plaid SDK for transactions sync API
from plaid.model.item_get_request import ItemGetRequest
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from datetime import date, timedelta

# Purpose of this file is to hold our credentials and automate verification to Plaid on every request.

_log = logging.getLogger(__name__)


def _parse_link_products():
    # PLAID_PRODUCTS=comma list (e.g. transactions,auth). Invalid tokens are skipped; default transactions.
    raw = os.getenv("PLAID_PRODUCTS", "transactions")
    out = []
    for part in raw.split(","):
        p = part.strip().lower()
        if not p:
            continue
        try:
            out.append(Products(p))
        except Exception:
            _log.warning("Skipping unknown Plaid product name: %s", p)
    return out if out else [Products("transactions")]


def _link_token_products():
    # Plaid rejects "balance" in link_token_create products — it is implied when other products are set.
    prods = _parse_link_products()
    filtered = [p for p in prods if getattr(p, "value", str(p)).lower() != "balance"]
    if not filtered:
        return [Products("transactions")]
    return filtered


def _parse_country_codes():
    # PLAID_COUNTRY_CODES=comma list of ISO country codes (e.g. US,CA). Default US.
    raw = os.getenv("PLAID_COUNTRY_CODES", "US")
    out = []
    for part in raw.split(","):
        p = part.strip().upper()
        if not p:
            continue
        try:
            out.append(CountryCode(p))
        except Exception:
            _log.warning("Skipping unknown Plaid country code: %s", p)
    return out if out else [CountryCode("US")]


def _resolve_plaid_environment(env_name):
    # Map PLAID_ENV string to plaid.Environment host (sandbox vs production).
    key = (env_name or os.getenv("PLAID_ENV") or "sandbox").strip().lower()
    if key in ("production", "prod"):
        return Environment.Production
    if key in ("development", "dev"):
        return Environment.Development
    return Environment.Sandbox


class PlaidConnector:  # credentials + verification to Plaid on every request
    
    def __init__(self, client_id, secret, environment):
        self.logger = logging.getLogger(__name__)
        self.client_id = client_id or os.getenv("PLAID_CLIENT_ID")
        self.secret = secret or os.getenv("PLAID_SECRET")
        self.environment = environment or os.getenv("PLAID_ENV")
        host = _resolve_plaid_environment(self.environment)
        self.config = Configuration(
            host=host,
            api_key={
                "clientId": self.client_id,
                "secret": self.secret,
            }
        )
        api_client = ApiClient(self.config)  # Plaid client for auth on every request
        self.client = plaid_api.PlaidApi(api_client)


    def create_link_token(self, client_user_id=None):
        """client_user_id should be the app user id (e.g. Supabase sub) when auth is enabled."""
        link_uid = (client_user_id or os.getenv("PLAID_LINK_USER_ID") or "USER").strip() or "USER"
        request = LinkTokenCreateRequest(
            user=LinkTokenCreateRequestUser(client_user_id=link_uid),
            client_name = "Automated Financial Analytics Engine",
            products=_link_token_products(),
            country_codes=_parse_country_codes(),
            language="en",
        )
        response = self.client.link_token_create(request)
        return response.link_token


    def exchange_public_token(self, public_token):#access_token //plaidDoc's made the method called that 
        try:
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self.client.item_public_token_exchange(request)
            return response.access_token, response.item_id
        except Exception as e:
            self.logger.error("Error exchanging public token", exc_info=True)
            raise


    def getAccounts(self, access_token): # Pull real time balance information for each account associated
        try:
            request = AccountsBalanceGetRequest(access_token=access_token)
            response = self.client.accounts_balance_get(request)
            return response.accounts  # real-time balance for each account
        except Exception as e:
            self.logger.error("Error getting accounts", exc_info=True)
            raise

    def fetch_institution_display_name(self, access_token):
        """Resolve human-readable institution name from Plaid (item + institutions/get_by_id)."""
        try:
            item_resp = self.client.item_get(ItemGetRequest(access_token=access_token))
            item = getattr(item_resp, "item", None)
            if not item:
                return None
            inst_id = getattr(item, "institution_id", None)
            if not inst_id:
                return None
            inst_resp = self.client.institutions_get_by_id(
                InstitutionsGetByIdRequest(
                    institution_id=str(inst_id),
                    country_codes=_parse_country_codes(),
                )
            )
            inst = getattr(inst_resp, "institution", None)
            if not inst:
                return None
            nm = getattr(inst, "name", None)
            if nm:
                return str(nm).strip() or None
        except Exception as e:
            self.logger.warning("Could not resolve institution display name from Plaid: %s", e)
        return None

    def remove_item(self, access_token):
        """Tell Plaid to invalidate the Item / access_token (call before deleting local plaid_items row)."""
        try:
            request = ItemRemoveRequest(access_token=access_token)
            self.client.item_remove(request)
        except Exception as e:
            self.logger.error("Error removing Plaid item", exc_info=True)
            raise

    def getTransactions(self, access_token, start_date=None, end_date=None, cursor=None):
        # Paginate /transactions/sync until has_more is false; return (tx list, next_cursor, removed plaid ids).
        try:
            all_tx = []
            removed_ids = []
            current_cursor = cursor if cursor is not None else ""
            last_next_cursor = ""

            while True:
                request = TransactionsSyncRequest(
                    access_token=access_token,
                    cursor=current_cursor
                )
                response = self.client.transactions_sync(request)
                if hasattr(response, 'added') and response.added:
                    all_tx.extend(response.added)                #//Sync API: new transactions
                if hasattr(response, 'modified') and response.modified:
                    all_tx.extend(response.modified)             # updated versions (removed not included)
                if hasattr(response, "removed") and response.removed:
                    for r in response.removed:
                        tid = getattr(r, "transaction_id", None)
                        if tid:
                            removed_ids.append(str(tid))
                last_next_cursor = getattr(response, "next_cursor", None) or last_next_cursor
                has_more = getattr(response, 'has_more', False)
                if not has_more:
                    break
                current_cursor = getattr(response, 'next_cursor', None) or getattr(response, 'cursor', None)
                if not current_cursor:
                    break
            if start_date or end_date:                          # filter by date after fetch (Sync API has no date range)
                if isinstance(start_date, str):
                    start_date = date.fromisoformat(start_date)
                if isinstance(end_date, str):
                    end_date = date.fromisoformat(end_date)
                if not end_date:
                    end_date = date.today()
                if not start_date:
                    start_date = end_date - timedelta(days=365) #plaid backtracks data from 1 year ago
                filtered_tx = []
                for tx in all_tx:
                    tx_date = getattr(tx, 'date', None) or getattr(tx, 'authorized_date', None)
                    if tx_date:
                        if isinstance(tx_date, str):
                            tx_date = date.fromisoformat(tx_date[:10])
                        elif hasattr(tx_date, 'date'):
                            tx_date = tx_date.date()
                        elif not isinstance(tx_date, date):
                            continue
                        if start_date <= tx_date <= end_date:
                            filtered_tx.append(tx)
                return filtered_tx, last_next_cursor, removed_ids
            return all_tx, last_next_cursor, removed_ids
        except Exception as e:
            self.logger.error("Error getting transactions", exc_info=True)
            raise

"""
HOW TRANSACTIONS WORK:
-we use access_token over item_id because item_id just keeps track of connections, 
whereas access_token is what allows us to access the sensative data from the connected institution,
access_token returns * transcations for that item(item is a plaid object representing a bank connection returning * transcations associated with a bank)
-//paginate: returns a big list of transcations in chunkcs(pages) since plaid only returns 500 transcations at a time
we than req the transcations in batches(500/e) untill reciving all transcations,
    whitch we than catoegorize via their accountID to link the transcations to correct account in the db
"""