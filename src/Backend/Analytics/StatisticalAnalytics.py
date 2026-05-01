import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .AnomalyDetector import AnomalyDetector

logger = logging.getLogger(__name__)

Transaction = Dict[str, Any]


def _parse_date(tx: Transaction) -> Optional[date]:
    raw = tx.get("date")
    if raw is None:
        return None
    if isinstance(raw, date):
        return raw
    s = str(raw)[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _parse_amount(tx: Transaction) -> float:
    try:
        return float(tx.get("amount", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _in_window(d: Optional[date], start: Optional[date], end: Optional[date]) -> bool:
    if d is None:
        return False
    if start and d < start:
        return False
    if end and d > end:
        return False
    return True


def _filter_tx(
    transactions: Sequence[Transaction],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[Transaction]:
    out: List[Transaction] = []
    for tx in transactions:
        d = _parse_date(tx)
        if _in_window(d, start_date, end_date):
            out.append(tx)
    return out


class StatisticalAnalytics:
    NET_CASH_FLOW = "net_cash_flow"
    INCOME_SUMMARY = "income_summary"
    EXPENSE_SUMMARY = "expense_summary"
    MONTHLY_SPEND = "monthly_spend"
    SAVINGS_RATE = "savings_rate"
    INCOME_EXPENSE_RATIO = "income_expense_ratio"
    CATEGORY_BREAKDOWN = "category_breakdown"
    CASH_FLOW_SERIES = "cash_flow_series"
    VOLATILITY = "volatility"
    ANOMALY_DETECTION = "anomaly_detection"
    MONTH_OVER_MONTH_CHANGE = "month_over_month_change"

    @staticmethod
    def _income_total(transactions: Sequence[Transaction]) -> float:
        """Plaid inflows: negative raw amount."""
        return sum(-_parse_amount(t) for t in transactions if _parse_amount(t) < 0)

    @staticmethod
    def _expense_total(transactions: Sequence[Transaction]) -> float:
        """Plaid outflows: positive raw amount."""
        return sum(_parse_amount(t) for t in transactions if _parse_amount(t) > 0)

    @staticmethod
    def net_cash_flow(
        transactions: Sequence[Transaction],
        month: Optional[str] = None,
        months: int = 1,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Human-friendly net = income - expenses (both positive magnitudes).
        If `month` is 'YYYY-MM', use that month; else optional explicit start/end.
        """
        if month:
            y, m = map(int, month.split("-")[:2])
            start = date(y, m, 1)
            if m == 12:
                end = date(y, 12, 31)
            else:
                end = date(y, m + 1, 1) - timedelta(days=1)
            subset = _filter_tx(transactions, start, end)
        elif start_date or end_date:
            subset = _filter_tx(transactions, start_date, end_date)
        else:
            if months and months > 0:
                end = date.today()
                start = end - timedelta(days=30 * months)
                subset = _filter_tx(transactions, start, end)
            else:
                subset = list(transactions)
        inc = StatisticalAnalytics._income_total(subset)
        exp = StatisticalAnalytics._expense_total(subset)
        return {
            "income": round(inc, 2),
            "expenses": round(exp, 2),
            "net": round(inc - exp, 2),
            "plaid_raw_sum": round(sum(_parse_amount(t) for t in subset), 2),
            "transaction_count": len(subset),
        }

    @staticmethod
    def income_summary(
        transactions: Sequence[Transaction],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        subset = _filter_tx(transactions, start_date, end_date)
        total = StatisticalAnalytics._income_total(subset)
        return {"total_income": round(total, 2), "count": sum(1 for t in subset if _parse_amount(t) < 0)}

    @staticmethod
    def expense_summary(
        transactions: Sequence[Transaction],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        subset = _filter_tx(transactions, start_date, end_date)
        total = StatisticalAnalytics._expense_total(subset)
        return {"total_expenses": round(total, 2), "count": sum(1 for t in subset if _parse_amount(t) > 0)}

    @staticmethod
    def monthly_spend(
        transactions: Sequence[Transaction],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, float]:
        subset = _filter_tx(transactions, start_date, end_date)
        buckets: Dict[str, float] = defaultdict(float)
        for tx in subset:
            d = _parse_date(tx)
            if not d:
                continue
            key = f"{d.year:04d}-{d.month:02d}"
            a = _parse_amount(tx)
            if a > 0:
                buckets[key] += a
        return dict(sorted(buckets.items()))

    @staticmethod
    def savings_rate(
        transactions: Sequence[Transaction],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        subset = _filter_tx(transactions, start_date, end_date)
        inc = StatisticalAnalytics._income_total(subset)
        exp = StatisticalAnalytics._expense_total(subset)
        if inc <= 0:
            return {"savings_rate": None, "reason": "no_income"}
        rate = (inc - exp) / inc
        return {"savings_rate": round(float(rate), 4), "income": round(inc, 2), "expenses": round(exp, 2)}

    @staticmethod
    def income_expense_ratio(
        transactions: Sequence[Transaction],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        subset = _filter_tx(transactions, start_date, end_date)
        inc = StatisticalAnalytics._income_total(subset)
        exp = StatisticalAnalytics._expense_total(subset)
        if exp <= 0:
            return {"ratio": None, "reason": "no_expenses"}
        return {"ratio": round(inc / exp, 4), "income": round(inc, 2), "expenses": round(exp, 2)}

    @staticmethod
    def category_breakdown(
        transactions: Sequence[Transaction],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        subset = _filter_tx(transactions, start_date, end_date)
        spend_by_cat: Dict[str, float] = defaultdict(float)
        for tx in subset:
            a = _parse_amount(tx)
            if a <= 0:
                continue
            cat = tx.get("category") or "UNCATEGORIZED"
            spend_by_cat[str(cat)] += a
        total = sum(spend_by_cat.values()) or 1.0
        share = {k: round(v / total, 4) for k, v in spend_by_cat.items()}
        return {"totals": {k: round(v, 2) for k, v in sorted(spend_by_cat.items(), key=lambda x: -x[1])}, "share": share}

    @staticmethod
    def cash_flow_series(
        transactions: Sequence[Transaction],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Daily human net (income - expense) then cumulative."""
        subset = _filter_tx(transactions, start_date, end_date)
        daily: Dict[date, float] = defaultdict(float)
        for tx in subset:
            d = _parse_date(tx)
            if not d:
                continue
            a = _parse_amount(tx)
            daily[d] += -a
        points: List[Tuple[date, float]] = sorted(daily.items())
        cum = 0.0
        series: List[Dict[str, Any]] = []
        for d, net in points:
            cum += net
            series.append({"date": d.isoformat(), "daily_net": round(net, 2), "cumulative": round(cum, 2)})
        return series

    @staticmethod
    def volatility(
        transactions: Sequence[Transaction],
        window_days: int = 30,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        subset = _filter_tx(transactions, start_date, end_date)
        daily_amt: Dict[date, float] = defaultdict(float)
        for tx in subset:
            d = _parse_date(tx)
            if not d:
                continue
            daily_amt[d] += _parse_amount(tx)
        vals = list(daily_amt.values())
        if len(vals) < 2:
            return {"stddev_daily_outflow": None, "days": len(vals)}
        return {"stddev_daily_outflow": float(np.std(np.array(vals, dtype=float))), "days": len(vals)}

    @staticmethod
    def anomaly_detection(
        transactions: Sequence[Transaction],
        threshold: float = 2.0,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        subset = _filter_tx(transactions, start_date, end_date)
        mags = [abs(_parse_amount(t)) for t in subset if _parse_amount(t) > 0]
        if len(mags) < 3:
            return {"flagged": [], "reason": "not_enough_spend_transactions"}
        mean = float(np.mean(mags))
        std = float(np.std(mags, ddof=1)) if len(mags) > 1 else 0.0
        flagged = AnomalyDetector.flag_transactions(subset, mean, std, threshold=threshold)
        return {"flagged": flagged[:50], "mean_abs_expense": round(mean, 2), "std_abs_expense": round(std, 2)}

    @staticmethod
    def month_over_month_change(
        transactions: Sequence[Transaction],
    ) -> Dict[str, Any]:
        monthly = StatisticalAnalytics.monthly_spend(transactions)
        if len(monthly) < 2:
            return {"pct_change": None, "reason": "need_two_months"}
        keys = sorted(monthly.keys())
        last, prev = keys[-1], keys[-2]
        this_v, prev_v = monthly[last], monthly[prev]
        if prev_v == 0:
            return {"pct_change": None, "this_month": last, "last_month": prev, "this_spend": this_v, "prev_spend": prev_v}
        pct = (this_v - prev_v) / prev_v
        return {
            "this_month": last,
            "last_month": prev,
            "this_spend": round(this_v, 2),
            "prev_spend": round(prev_v, 2),
            "pct_change": round(float(pct), 4),
        }
