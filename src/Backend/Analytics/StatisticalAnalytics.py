import numpy as np 
import logging

from datetime import date, timedelta, datetime
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Sequence

#TYPE ALIASING
Transaction = Dict[str, any] # TYPE ALIASING: as dicts key==str, value==anything

logger = logging.getLogger(__name__)
#now we start v
























class StatisticalAnalytics:

    NET_CASH_FLOW = "net_cash_flow"                         #for enum category
    INCOME_SUMMARY = "income_summary"
    EXPENSE_SUMMARY = "expense_summary"
    MONTHLY_SPEND = "monthly_spend"
    SAVINGS_RATE = "savings_rate"
    INCOME_EXPENSE_RATIO = "income_expense_ratio"
    CATEGORY_BREAKDOWN = "category_breakdown"
    CASH_FLOW_SERIES = "cash_flow_series"
    VOLATILITY = "volatility"
    ANOMALY_DETECTION = "anomaly_detection"
    MONTH_OVER_MONTH_CHANGE = "month_over_month_change"    #for enum category


    @staticmethod
    def net_cash_flow(transactions, month, months): #memebrs dont mean anything yet, currently decalring them
        ...



    @staticmethod
    def income_summary():
        ...
    
    
    @staticmethod
    def expense_summary():
        ...


    @staticmethod
    def monthly_spend():
        ...


    @staticmethod
    def savings_rate():
        ...


    @staticmethod
    def income_expense_ratio():
        ...


    @staticmethod
    def category_breakdown():
        ...


    @staticmethod
    def cash_flow_series():
        ...

    @staticmethod
    def volatility():
        ...


    @staticmethod
    def anomaly_detection():
        ...

    @staticmethod
    def month_over_month_change():
        ...

#------------------------------------NOTES----------------------------------------------------------------------------------------#
"""
every method has @staticmethod because we want the methods to be stateles,
and used purely as a calulator to perform its forumla's to obtian an answer
------------------------------------------------

"""


"""
                                       STATISTICAL ANALYTICS FORUMLS
============================================================================================================================
-Net Cash Flow = sum(amount)
-Income = sum(amount where amount > 0)
-Expenses = sum(amount where amount < 0)
-Monthly Spend = sum(amount) grouped by month
start_date = end_date

-Burn Rate = abs(total expenses over last 30 days) / 30
-Savings Rate = (Income - abs(Expenses)) / Income
-Ratio = Income / abs(Expenses)
-Category Total = sum(amount grouped by category)
-Category Share = Category Total / Total Spending
-RollingAvg_7d(t) = (sum of amounts from t-6 through t) / 7
-Cumulative(t) = sum of all transaction amounts from start through time t
-Volatility = sqrt( average( (x - mean)^2 ) )
-Z = (x - mean) / standard_deviation        //Anomaly Detection
Flag anomaly if abs(Z) > 2

-Month Over Month Change = (ThisMonth - LastMonth) / LastMonth
"""