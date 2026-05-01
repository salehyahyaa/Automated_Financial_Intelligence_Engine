"""Dashboard JSON handler (registered on app in main.py so it survives stale route imports)."""
import logging
from typing import Optional

from fastapi import Depends, HTTPException

from auth_supabase import get_supabase_user_sub_optional

logger = logging.getLogger(__name__)


def get_dashboard_summary(user_sub: Optional[str] = Depends(get_supabase_user_sub_optional)):
    """Light JSON for the dashboard: accounts, recent txs, 90d snapshot (no LLM)."""
    from deps import dataAutomation
    from services.finance_context import build_finance_context

    try:
        result = dataAutomation.get_latest_plaid_item(user_sub)
    except Exception as e:
        err_txt = str(e)
        if "Database not configured" in err_txt:
            return {
                "linked": False,
                "database_configured": False,
                "accounts": [],
                "recent_transactions": [],
                "snapshot": None,
            }
        logger.error("dashboard_summary DB error", exc_info=True)
        raise HTTPException(500, detail=err_txt)
    if not result:
        return {
            "linked": False,
            "database_configured": True,
            "accounts": [],
            "recent_transactions": [],
            "snapshot": None,
        }
    plaid_items_id_column, _access = result
    ctx = build_finance_context(dataAutomation, plaid_items_id_column)
    accounts = ctx.get("accounts") or []
    institution = dataAutomation.fetch_plaid_item_meta(plaid_items_id_column)
    recent = dataAutomation.fetch_recent_transactions_dashboard(plaid_items_id_column, 25)
    s90 = (ctx.get("summary") or {}).get("last_90_days") or {}
    liquid = 0.0
    for a in accounts:
        bal = a.get("current_balance")
        if bal is not None:
            try:
                liquid += float(bal)
            except (TypeError, ValueError):
                pass
    return {
        "linked": True,
        "database_configured": True,
        "institution": institution,
        "accounts": accounts,
        "recent_transactions": recent,
        "snapshot": {
            "accounts_connected": len(accounts),
            "total_liquid_estimate": round(liquid, 2),
            "transaction_row_count": ctx.get("transaction_row_count", 0),
            "income_90d": s90.get("income"),
            "expenses_90d": s90.get("expenses"),
            "net_90d": s90.get("net"),
        },
    }
