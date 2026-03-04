import plaid 
import os
import logging
from plaid.model.country_code import CountryCode  
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid import ApiClient, Configuration
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.products import Products
from plaid import Environment
from plaid.model.transactions_sync_request import TransactionsSyncRequest  # Plaid SDK for transactions sync API
from datetime import date, timedelta
#Purpose of this file is to hold our credientals and automate our verification to plaid everytime we send a req


class PlaidConnector:  # credentials + verification to Plaid on every request
    
    def __init__(self, client_id, secret, environment):
        self.logger = logging.getLogger(__name__)
        self.client_id = os.getenv("PLAID_CLIENT_ID")
        self.secret = os.getenv("PLAID_SECRET")
        self.config = Configuration(
            host=Environment.Production,
            api_key={
                "clientId": self.client_id,
                "secret": self.secret,
            }
        )
        api_client = ApiClient(self.config)  # Plaid client for auth on every request
        self.client = plaid_api.PlaidApi(api_client)


    def create_link_token(self):                                                             #PlaidDoc's made the method called create_link_token, we just call it here to use it
        request = LinkTokenCreateRequest(
            user=LinkTokenCreateRequestUser(client_user_id="USER"), 
            client_name="Automated Financial Analytics Engine",
            products=[Products("transactions")],  # which Plaid products; add Products("auth") later if needed
            country_codes=[CountryCode("US")],
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
 
 
    def getTransactions(self, access_token, start_date=None, end_date=None, cursor=None):
        """Fetch transactions via access_token, returning transactions for * accounts under that Item. Paginates * transcations to accountID to link the transactions-accounts"""
        try:
            all_tx = []
            current_cursor = cursor or ""  # empty cursor = initial full sync
            
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
                return filtered_tx    
            return all_tx
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