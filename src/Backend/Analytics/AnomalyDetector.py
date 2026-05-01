"""
Z-score based flags using precomputed mean/std from descriptive analytics.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Uses μ and σ supplied by StatisticalAnalytics (or callers); does not compute series stats itself."""

    @staticmethod
    def z_score(value: float, mean: float, stddev: float) -> Optional[float]:
        if stddev is None or stddev == 0:
            return None
        return (float(value) - float(mean)) / float(stddev)

    @staticmethod
    def is_anomaly(z: Optional[float], threshold: float = 2.0) -> bool:
        if z is None:
            return False
        return abs(z) > threshold

    @staticmethod
    def flag_amounts(
        values: Sequence[float],
        mean: float,
        stddev: float,
        threshold: float = 2.0,
    ) -> List[int]:
        """Return indices where |Z| > threshold."""
        out: List[int] = []
        for i, v in enumerate(values):
            z = AnomalyDetector.z_score(v, mean, stddev)
            if AnomalyDetector.is_anomaly(z, threshold):
                out.append(i)
        return out

    @staticmethod
    def flag_transactions(
        transactions: Sequence[Dict[str, Any]],
        mean_amount: float,
        std_amount: float,
        threshold: float = 2.0,
        amount_key: str = "amount",
    ) -> List[Dict[str, Any]]:
        """
        Flag individual transactions whose |amount| is unusual vs amount distribution.
        Uses absolute amount magnitudes for deviation (typical for spend spikes).
        """
        if std_amount is None or std_amount == 0:
            return []
        flagged: List[Dict[str, Any]] = []
        for tx in transactions:
            try:
                raw = float(tx.get(amount_key, 0) or 0)
            except (TypeError, ValueError):
                continue
            mag = abs(raw)
            z = AnomalyDetector.z_score(mag, mean_amount, std_amount)
            if AnomalyDetector.is_anomaly(z, threshold):
                flagged.append(
                    {
                        "plaid_transaction_id": tx.get("plaid_transaction_id"),
                        "date": str(tx.get("date")),
                        "amount": raw,
                        "merchant_name": tx.get("merchant_name"),
                        "category": tx.get("category"),
                        "z_score": round(z, 3) if z is not None else None,
                    }
                )
        return flagged
