import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status
from starlette.responses import StreamingResponse

from auth_supabase import get_supabase_user_sub_optional
from deps import bank, dataAutomation

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/create_link_token", status_code=200)
def createLinkToken(user_sub: Optional[str] = Depends(get_supabase_user_sub_optional)):
    try:
        link_token = bank.create_link_token(client_user_id=user_sub)
        if link_token is None:
            raise HTTPException(500, detail="Link Token Failed to create")
        return {"link_token": link_token}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating link token", exc_info=True)
        raise HTTPException(500, detail=f"ServerSide Error: {str(e)}")


@router.post("/exchange_public_token", status_code=200)
def getAccessToken(body: dict, user_sub: Optional[str] = Depends(get_supabase_user_sub_optional)):
    try:
        public_token = body.get("public_token")
        if not public_token:
            raise HTTPException(400, detail="frontend needs PUBLIC TOKEN to request accessToken")

        access_token, plaid_item_id = bank.exchange_public_token(public_token)

        if access_token is None:
            raise HTTPException(500, detail="Server error")

        plaid_items_id_column = dataAutomation.store_plaid_item_id(plaid_item_id, app_user_id=user_sub)
        dataAutomation.store_access_token(access_token, plaid_items_id_column)
        try:
            inst_label = bank.fetch_institution_display_name(access_token)
            if inst_label:
                dataAutomation.update_plaid_item_label(plaid_items_id_column, inst_label, inst_label)
        except Exception as ex:
            logger.warning("Could not persist institution name after token exchange: %s", ex)
        return {"access_token": access_token}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error exchanging public token", exc_info=True)
        raise HTTPException(500, detail=f"Server error: {str(e)}")


def _sync_checking_impl(user_sub: Optional[str]):
    result = dataAutomation.get_latest_plaid_item(user_sub)
    if not result:
        raise HTTPException(404, detail="No linked item_id found. Link a bank first.")
    plaid_items_id_column, access_token = result
    accounts = bank.getAccounts(access_token)
    checking_accounts = [
        account for account in accounts if account.type and str(account.type).lower() == "depository"
    ]
    dataAutomation.store_checking_accounts(checking_accounts, plaid_items_id_column)
    if dataAutomation.plaid_item_label_is_blank(plaid_items_id_column):
        try:
            inst_label = bank.fetch_institution_display_name(access_token)
            if inst_label:
                dataAutomation.update_plaid_item_label(plaid_items_id_column, inst_label, inst_label)
        except Exception as ex:
            logger.warning("Could not backfill institution name after checking sync: %s", ex)
    return len(checking_accounts)


def _sync_credit_impl(user_sub: Optional[str]):
    result = dataAutomation.get_latest_plaid_item(user_sub)
    if not result:
        raise HTTPException(404, detail="No linked item found. Link a bank first.")
    plaid_items_id_column, access_token = result
    accounts = bank.getAccounts(access_token)
    credit_accounts = [account for account in accounts if account.type and str(account.type).lower() == "credit"]
    dataAutomation.store_credit_accounts(credit_accounts, plaid_items_id_column)
    return len(credit_accounts)


def _sync_transactions_impl(user_sub: Optional[str], body: dict | None):
    result = dataAutomation.get_latest_plaid_item(user_sub)
    if not result:
        raise HTTPException(404, detail="No linked item found. Link a bank first.")
    plaid_items_id_column, access_token = result
    body = body or {}
    try:
        stored_cursor = dataAutomation.get_transactions_sync_cursor(plaid_items_id_column)
    except Exception:
        stored_cursor = ""
    raw, next_cursor, removed_ids = bank.getTransactions(
        access_token,
        start_date=body.get("start_date"),
        end_date=body.get("end_date"),
        cursor=stored_cursor or None,
    )
    if removed_ids:
        dataAutomation.delete_transactions_by_plaid_ids(plaid_items_id_column, removed_ids)
    normalized = _clean_plaid_transactions(raw)
    stored = dataAutomation.store_transactions(normalized, plaid_items_id_column)
    if next_cursor:
        dataAutomation.set_transactions_sync_cursor(plaid_items_id_column, next_cursor)
    return {
        "stored": stored,
        "fetched": len(raw),
        "removed": len(removed_ids),
        "cursor_saved": bool(next_cursor),
    }


@router.post("/sync_checking_accounts", status_code=200)
def getCheckingAccounts(user_sub: Optional[str] = Depends(get_supabase_user_sub_optional)):
    try:
        n = _sync_checking_impl(user_sub)
        return {"stored": n}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error syncing checking accounts", exc_info=True)
        raise HTTPException(500, detail=f"Server error: {str(e)}")


@router.post("/sync_credit_accounts", status_code=200)
def getCreditAccounts(user_sub: Optional[str] = Depends(get_supabase_user_sub_optional)):
    try:
        n = _sync_credit_impl(user_sub)
        return {"stored": n}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error syncing credit accounts", exc_info=True)
        raise HTTPException(500, detail=f"Server error: {str(e)}")


@router.post("/sync-transactions", status_code=200)
def syncTransactions(body: dict = None, user_sub: Optional[str] = Depends(get_supabase_user_sub_optional)):
    """Sync transactions for the current user's latest linked Plaid item."""
    try:
        return _sync_transactions_impl(user_sub, body)
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


@router.post("/refresh_account_data", status_code=200)
def refreshAccountData(user_sub: Optional[str] = Depends(get_supabase_user_sub_optional)):
    _sync_checking_impl(user_sub)
    _sync_credit_impl(user_sub)
    _sync_transactions_impl(user_sub, {})
    logger.info("Refreshing account data")
    return {"Refreshed Acc Data": True}


def _chat_message_and_finance(body: dict, user_sub: Optional[str]):
    """Validate message, load DB + finance context for chat (sync or stream)."""
    msg = (body or {}).get("message") or (body or {}).get("content") or ""
    msg = str(msg).strip()
    if not msg:
        raise HTTPException(400, detail="message is required")
    try:
        result = dataAutomation.get_latest_plaid_item(user_sub)
    except Exception as db_err:
        err_txt = str(db_err)
        if "Database not configured" in err_txt:
            logger.error("Chat blocked: database not configured", exc_info=True)
            raise HTTPException(
                503,
                detail=(
                    "Database not configured. Add DATABASE_URL (Supabase connection string) "
                    "to the .env file at the **repository root** (same folder as README), then restart the server. "
                    "In Supabase you must also run your SQL schema on the project database."
                ),
            )
        raise
    if not result:
        finance = {"note": "No linked bank; user should connect Plaid first."}
    else:
        plaid_items_id_column, _access = result
        from services.finance_context import build_finance_context

        finance = build_finance_context(dataAutomation, plaid_items_id_column)
    return msg, finance


@router.post("/chat", status_code=200)
def chat(body: dict, user_sub: Optional[str] = Depends(get_supabase_user_sub_optional)):
    # User message + OpenAI reply using FINANCE_CONTEXT from latest linked Plaid item.
    try:
        msg, finance = _chat_message_and_finance(body, user_sub)
        from LLM.prompts import FINANCE_ASSISTANT_SYSTEM
        from LLM.client import chat_completion

        reply = chat_completion(msg, FINANCE_ASSISTANT_SYSTEM, finance)
        return {"reply": reply}
    except HTTPException:
        raise
    except RuntimeError as e:
        logger.error("Chat configuration error", exc_info=True)
        raise HTTPException(503, detail=str(e))
    except Exception as e:
        logger.error("Chat failed", exc_info=True)
        raise HTTPException(500, detail=str(e))


@router.post("/chat/stream")
def chat_stream(body: dict, user_sub: Optional[str] = Depends(get_supabase_user_sub_optional)):
    """SSE stream of OpenAI deltas: data: {\"type\":\"start|delta|done|error\",...}\\n\\n"""

    def event_gen():
        try:
            msg, finance = _chat_message_and_finance(body, user_sub)
        except HTTPException as he:
            yield f"data: {json.dumps({'type': 'error', 'message': str(he.detail)})}\n\n"
            return
        except Exception as e:
            logger.error("Chat stream setup failed", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return
        try:
            from LLM.prompts import FINANCE_ASSISTANT_SYSTEM
            from LLM.client import chat_completion_stream

            yield f"data: {json.dumps({'type': 'start'})}\n\n"
            for piece in chat_completion_stream(msg, FINANCE_ASSISTANT_SYSTEM, finance):
                yield f"data: {json.dumps({'type': 'delta', 'content': piece})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except RuntimeError as e:
            logger.error("Chat stream configuration error", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        except Exception as e:
            logger.error("Chat stream failed", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


#reflect current balance w/Pending //currently refelcting only posted 
#encryt security data in db 
#documentation on probelms faced with DB with refresh logic not refreshing and then after SQL logic in dataAutomation.py was fixed,
# how you also had to add constriations to table schema to fix the issue, why is the table schema issue a probelm?
#alter id to accuralty reflect number of accounts


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



