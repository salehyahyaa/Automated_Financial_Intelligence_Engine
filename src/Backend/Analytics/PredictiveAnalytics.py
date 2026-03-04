"""
========================================  
LAYER 2 — PREDICTIVE (Future Estimation)
========================================

1. Simple Baseline Projection
NextMonth = Rolling 3-Month Average

2. Linear Regression (Trend Line)
PredictedValue = intercept + slope * time
y = b0 + b1 * t

3. Balance Projection
FutureBalance = CurrentBalance + ProjectedInflows - ProjectedOutflows

4. Cash Runway
RunwayMonths = CurrentCash / MonthlyBurn

5. Spending Trend
Trend = slope (b1 from regression)
If slope > 0 → spending increasing
If slope < 0 → spending decreasing

6. Seasonality (Monthly Pattern)
AvgSpendForMonth_m = total spend in month m across years / number of years

7. Prediction Range (Uncertainty)
ProjectionRange = Prediction ± (k * volatility)
k = 1 (normal range)
k = 2 (conservative range)
"""

