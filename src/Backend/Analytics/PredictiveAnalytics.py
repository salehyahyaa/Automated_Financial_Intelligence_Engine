"""
Layer 2 — projections from recent history (baselines, simple trend, runway).
All amounts use the same transaction dict shape as StatisticalAnalytics.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _parse_date(tx: Dict[str, Any]) -> Optional[date]:
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


def _expense_magnitude(tx: Dict[str, Any]) -> float:
    """Plaid: positive amount = outflow (spend). Return spend as positive float."""
    try:
        a = float(tx.get("amount", 0) or 0)
    except (TypeError, ValueError):
        return 0.0
    return a if a > 0 else 0.0


def _inflow_magnitude(tx: Dict[str, Any]) -> float:
    try:
        a = float(tx.get("amount", 0) or 0)
    except (TypeError, ValueError):
        return 0.0
    return -a if a < 0 else 0.0


class PredictiveAnalytics:
    SAVINGS_PROJECTION = "savings_projection"
    BALANCE_PROJECTION = "balance_projection"
    RUNWAY = "runway"
    SPENDING_TREND = "spending_trend"
    SEASONALITY_ANALYSIS = "seasonality_analysis"

    @staticmethod
    def monthly_total_spend_by_month(transactions: Sequence[Dict[str, Any]]) -> Dict[str, float]:
        buckets: Dict[str, float] = defaultdict(float)
        for tx in transactions:
            d = _parse_date(tx)
            if not d:
                continue
            buckets[_month_key(d)] += _expense_magnitude(tx)
        return dict(sorted(buckets.items()))

    @staticmethod
    def spending_trend(transactions: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        """
        OLS slope on month index vs total monthly spend (last up to 12 non-empty months).
        Positive slope => spend increasing.
        """
        monthly = PredictiveAnalytics.monthly_total_spend_by_month(transactions)
        if len(monthly) < 2:
            return {"slope": None, "months_used": len(monthly), "note": "need at least 2 months"}
        keys = list(monthly.keys())[-12:]
        y = np.array([monthly[k] for k in keys], dtype=float)
        x = np.arange(len(y), dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        return {
            "slope": float(slope),
            "intercept": float(intercept),
            "months_used": len(keys),
            "last_month_key": keys[-1],
            "last_month_spend": float(monthly[keys[-1]]),
        }

    @staticmethod
    def savings_projection(transactions: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        """Next month net ≈ average of last 3 complete calendar months (income - spend as positive net)."""
        monthly_net: Dict[str, float] = defaultdict(float)
        for tx in transactions:
            d = _parse_date(tx)
            if not d:
                continue
            mk = _month_key(d)
            try:
                a = float(tx.get("amount", 0) or 0)
            except (TypeError, ValueError):
                continue
            monthly_net[mk] += -a
        if not monthly_net:
            return {"projected_next_month_net": None, "basis_months": []}
        ordered = sorted(monthly_net.keys())[-3:]
        vals = [monthly_net[k] for k in ordered]
        proj = float(np.mean(vals)) if vals else None
        return {"projected_next_month_net": proj, "basis_months": ordered, "monthly_net": {k: float(monthly_net[k]) for k in ordered}}

    @staticmethod
    def seasonality_analysis(transactions: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        """Average expense magnitude per calendar month (1–12) across years in sample."""
        sums: Dict[int, List[float]] = defaultdict(list)
        for tx in transactions:
            d = _parse_date(tx)
            if not d:
                continue
            sums[d.month].append(_expense_magnitude(tx))
        avgs: Dict[str, float] = {}
        for m in range(1, 13):
            if sums[m]:
                avgs[str(m)] = float(np.mean(sums[m]))
        return {"avg_spend_by_calendar_month": avgs}

    @staticmethod
    def runway(current_cash: float, monthly_burn: float) -> Dict[str, Any]:
        """
        RunwayMonths = current_cash / monthly_burn (burn as positive monthly expense).
        """
        if monthly_burn is None or monthly_burn <= 0:
            return {"runway_months": None, "reason": "no_positive_burn"}
        return {"runway_months": float(current_cash) / float(monthly_burn), "current_cash": float(current_cash), "monthly_burn": float(monthly_burn)}

    @staticmethod
    def balance_projection(
        current_liquid_balance: float,
        projected_monthly_inflow: float,
        projected_monthly_outflow: float,
        months_ahead: int = 3,
    ) -> Dict[str, Any]:
        """
        Simple forward balance: balance + m*(inflow - outflow), inflow/outflow as positive magnitudes.
        """
        net_per_month = float(projected_monthly_inflow) - float(projected_monthly_outflow)
        series = []
        bal = float(current_liquid_balance)
        for m in range(1, months_ahead + 1):
            bal += net_per_month
            series.append({"month": m, "projected_balance": round(bal, 2)})
        return {"starting_balance": float(current_liquid_balance), "net_per_month": net_per_month, "series": series}
