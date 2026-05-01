"""Linked accounts list + delink (registered on app in main.py so routes always resolve)."""
import logging
from typing import Optional

from fastapi import Depends, HTTPException

from auth_supabase import get_supabase_user_sub_optional
from deps import bank, dataAutomation

logger = logging.getLogger(__name__)


def list_linked_accounts(user_sub: Optional[str] = Depends(get_supabase_user_sub_optional)):
    """All Plaid-linked accounts for the current app user (for settings / delink UI)."""
    try:
        rows = dataAutomation.fetch_linked_accounts_for_app_user(user_sub)
        return {"accounts": rows}
    except Exception as e:
        logger.error("list_linked_accounts failed", exc_info=True)
        raise HTTPException(500, detail=str(e)) from e


def delink_account(account_id: int, user_sub: Optional[str] = Depends(get_supabase_user_sub_optional)):
    """
    Remove the Plaid Item that owns this account row (Plaid has no per-account unlink).
    Deletes local plaid_items (cascades accounts and transactions).
    """
    try:
        pair = dataAutomation.get_plaid_item_for_account_delink(account_id, user_sub)
        if not pair:
            raise HTTPException(404, detail="Account not found or you cannot remove this link.")
        plaid_items_pk, access_token = pair
        if access_token:
            try:
                bank.remove_item(access_token)
            except Exception as pe:
                logger.warning("Plaid item_remove failed; removing local link anyway: %s", pe)
        dataAutomation.delete_plaid_item_row(plaid_items_pk)
        return {"ok": True, "removed_plaid_item_pk": plaid_items_pk}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delink_account failed", exc_info=True)
        raise HTTPException(500, detail=str(e)) from e
