from PlaidConnector import PlaidConnector
from fastapi import APIRouter, HTTPException
from fastapi import status 
from dotenv import load_dotenv
import os
import logging
from database.Connection import Connection 
from DataAutomation import DataAutomation 
import psycopg2

logger = logging.getLogger(__name__)

router = APIRouter()
db = Connection() 
load_dotenv()
PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")
PLAID_ENV = os.getenv("PLAID_ENV")

bank = PlaidConnector(PLAID_CLIENT_ID, PLAID_SECRET, PLAID_ENV)
dataAutomation = DataAutomation(db)



@router.get("/create_link_token", status_code = 200)                            #putting data in the html btn to get to plaid
def createLinkToken():
    try:
        link_token = bank.create_link_token()                                   #assign the LinkToken to var to return it
        if link_token == None: 
            raise HTTPException(500, detail = "Link Token Failed to create")    #only if we have no token returned #tackling potionel error's before actully telling endpoint what to do
        return {"link_token": link_token}                                       #return link_token 
    except Exception as e:
        logger.error("Error creating link token", exc_info=True)
        raise HTTPException(500, detail = f"ServerSide Error: {str(e)}")

 
@router.post("/exchange_public_token", status_code = 200)                       #giving plaid our verificaiton("acess_token") -> get access to accounts
def getAccessToken(body: dict):                                                 #accepting Access_tokens as dicts
    try:
        public_token = body.get("public_token")
        if not public_token:                                                    #publicKey is what we send to Plaid to recive accessToken to login
            raise HTTPException(400, detail = "frontend needs PUBLIC TOKEN to request accessToken")

        access_token, plaid_item_id = bank.exchange_public_token(public_token)       #Assigmation is atomic either both get values or NONE
        
        if access_token == None:
            raise HTTPException(500, detail="Server error")
        
        plaid_items_id_column = dataAutomation.store_plaid_item_id(plaid_item_id)   #tracks inserated row of plaid_item_id so when  ID column auto increments we can store that ID and return it to plaid_items_id_column
        dataAutomation.store_access_token(access_token, plaid_items_id_column)   
        return {"access_token": access_token}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error exchanging public token", exc_info=True)
        raise HTTPException(500, detail=f"Server error: {str(e)}")


@router.post("/sync_checking_accounts", status_code=200)
def getCheckingAccounts():
    try:
        result = dataAutomation.get_latest_plaid_item()
        if not result:
            raise HTTPException(404, detail="No linked item_id found. Link a bank first.")
        plaid_items_id_column, access_token = result
        accounts = bank.getAccounts(access_token)
        checking_accounts = [account for account in accounts if account.type and str(account.type).lower() == "depository"] #plaid uses depository to identify checking accounts
        dataAutomation.store_checking_accounts(checking_accounts, plaid_items_id_column)
        return {"stored": len(checking_accounts)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error syncing checking accounts", exc_info=True)
        raise HTTPException(500, detail=f"Server error: {str(e)}")


@router.post("/sync_credit_accounts", status_code=200)
def getCreditAccounts():
    try:
        result = dataAutomation.get_latest_plaid_item()
        if not result:
            raise HTTPException(404, detail="No linked item found. Link a bank first.")
        plaid_items_id_column, access_token = result
        accounts = bank.getAccounts(access_token)
        credit_accounts = [account for account in accounts if account.type and str(account.type).lower() == "credit"] #plaid uses credit to identify credit accounts
        dataAutomation.store_credit_accounts(credit_accounts, plaid_items_id_column)
        return {"stored": len(credit_accounts)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error syncing credit accounts", exc_info=True)
        raise HTTPException(500, detail=f"Server error: {str(e)}")


@router.post("/sync-transactions", status_code=200)
def syncTransactions(body: dict = None):
    """Catogorizes transcations recived from _clean_plaid_transactions to the bank account they came from whitch we know because of accountID, 
       and then store related transcation data in the correct columns within the accounts table in our db, but only for the most recently linked item"""
    try:
        result = dataAutomation.get_latest_plaid_item()
        if not result:
            raise HTTPException(404, detail="No linked item found. Link a bank first.")
        plaid_items_id_column, access_token = result
        body = body or {}
        raw = bank.getTransactions(access_token, start_date=body.get("start_date"), end_date=body.get("end_date"))
        normalized = _clean_plaid_transactions(raw)
        stored = dataAutomation.store_transactions(normalized, plaid_items_id_column)
        return {"stored": stored, "fetched": len(raw)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error syncing transactions", exc_info=True)
        raise HTTPException(500, detail=f"Server error: {str(e)}")


def _clean_plaid_transactions(raw):
    """raw transcational data from getTransactions() formatted in Plaids format whitch we turn into our desired dict data format to feed it into the sync-transactions
       tx = transaction(s), cat = category"""
    normalized = []
    for tx in raw:
        tid = getattr(tx, "transaction_id", None)
        amount = getattr(tx, "amount", None)
        tx_date = getattr(tx, "date", None) or getattr(tx, "authorized_date", None)
        if tid is None or amount is None or tx_date is None:
            continue
        if hasattr(tx_date, "strftime"):
            date_str = tx_date.strftime("%Y-%m-%d")
        else:
            date_str = str(tx_date)[:10]
        tx_time = None
        dt = getattr(tx, "datetime", None) or getattr(tx, "authorized_datetime", None)
        if dt and hasattr(dt, "strftime"):
            tx_time = dt.strftime("%H:%M:%S")
        cat = None
        if getattr(tx, "personal_finance_category", None) and getattr(tx.personal_finance_category, "primary", None):
            cat = getattr(tx.personal_finance_category.primary, "value", None) or str(tx.personal_finance_category.primary)
        elif getattr(tx, "category", None):
            cat = tx.category[0] if isinstance(tx.category, list) and tx.category else str(tx.category)
        pending = bool(getattr(tx, "pending", False))
        normalized.append({
            "plaid_account_id": getattr(tx, "account_id", None),
            "plaid_transaction_id": tid,
            "date": date_str,
            "amount": amount,
            "transaction_time": tx_time,
            "merchant_name": getattr(tx, "merchant_name", None),
            "category": cat,
            "status": "pending" if pending else "posted",
            "iso_currency_code": getattr(tx, "iso_currency_code", None) or getattr(tx, "unofficial_currency_code", None) or "USD",
        })
    return normalized


    #refresh balance endpoint

#------------------------------------NOTES----------------------------------------------------------------------------------------#
"""
-so everytime we create a link token //by starting program and clicking the connect bank account button
-we are prompted to enter user login credentials(public token) whitch plaid exchanges into access_token to securly log in
-plaid then creates an item_id(unique identifier) to represent every successful connection to a finaincal institution
-from that item_id our syncCredit/Checking endpoints processes every new linked connection    //endpoints are statless so every endpoint sends the data recived to the db thanks to our DataAutomation class
    for every iteration the sync_credit will filter for credit accounts and the sync_checking will filter for checking accounts
    then it will add those accounts to the proper columns in the accounts table
"""


"""
HOW WE CLEAN TRNASCATOINS DATA, ASSIGN IT TO THE CORRECT ACCOUNT, AND STORE IT IN THE DB:
-So basically what you’re saying is we use PlaidConnector.py 's function getTransactions() to pull all the transactions from Plaid’s Item. 
    An Item is an object from Plaid that holds a list of * the transactions across all accounts togther PER BANK (in 1 list), 
-Then in Endpoints.py we use _clean_plaid_transactions to take that list of transactions per financial institution and turn it from Plaid’s format into our desired dictionary format. 
- After that, the syncTransactions endpoint categorizes each transaction into the correct account column (and the other columns) in the database based on the transaction dict’s account ID.

"""