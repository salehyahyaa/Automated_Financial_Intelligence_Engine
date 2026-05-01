"""
Build a JSON-serializable snapshot for the LLM from the latest Plaid-linked data in Postgres.
"""
from datetime import date, timedelta

from Analytics.PredictiveAnalytics import PredictiveAnalytics
from Analytics.StatisticalAnalytics import StatisticalAnalytics


def build_finance_context(data_automation, plaid_items_id_column):
    # Pull rows from DB, summarize with analytics, include a small recent tx sample for Q&A.
    transactions = data_automation.fetch_transactions_for_analytics(plaid_items_id_column)
    accounts = data_automation.fetch_account_balances(plaid_items_id_column)
    end = date.today()
    start = end - timedelta(days=90)
    recent = []
    for row in transactions[-80:]:
        recent.append(
            {
                "date": row.get("date"),
                "amount": row.get("amount"),
                "merchant_name": row.get("merchant_name"),
                "category": row.get("category"),
                "account_name": row.get("account_name"),
            }
        )
    liquid = 0.0
    for a in accounts:
        bal = a.get("current_balance")
        if bal is not None:
            try:
                liquid += float(bal)
            except (TypeError, ValueError):
                pass
    summary = {
        "last_90_days": StatisticalAnalytics.net_cash_flow(transactions, start_date=start, end_date=end),
        "income": StatisticalAnalytics.income_summary(transactions, start_date=start, end_date=end),
        "expenses": StatisticalAnalytics.expense_summary(transactions, start_date=start, end_date=end),
        "savings_rate": StatisticalAnalytics.savings_rate(transactions, start_date=start, end_date=end),
        "category_breakdown": StatisticalAnalytics.category_breakdown(transactions, start_date=start, end_date=end),
        "monthly_spend": StatisticalAnalytics.monthly_spend(transactions, start_date=start, end_date=end),
        "month_over_month": StatisticalAnalytics.month_over_month_change(transactions),
        "spending_trend": PredictiveAnalytics.spending_trend(transactions),
    }
    monthly_burn = float(summary["last_90_days"].get("expenses", 0) or 0) / 3.0
    if monthly_burn > 0:
        summary["runway_estimate_months"] = PredictiveAnalytics.runway(liquid, monthly_burn)
    else:
        summary["runway_estimate_months"] = {"runway_months": None, "reason": "no_burn_estimate"}
    return {
        "accounts": accounts,
        "summary": summary,
        "recent_transactions_sample": recent,
        "transaction_row_count": len(transactions),
    }
