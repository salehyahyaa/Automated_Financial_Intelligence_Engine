# Automated Financial Intelligence Engine
-A backend engine that securely ingests financial data from multiple institutions via plaid, centralizing all personal financial activity into a unified system. The platform applies statistical analysis and predictive modeling to generate portfolio insights, and integrates LLMs (Gemini) to enable naturallanguage financial queries and personalized, datadriven intelligence on individual finances.


## Architecture
- Python
- PostgreSQL
- Plaid 
- Gemini


## Features
- Secure OAuth financial data ingestion
- Real time streaming ingestion
- Predictive Financial Modeling
- Automated Transaction Classification
- Portfolio performance analytics
- Quantitive timeseries forecasting (ARIMA / ML models)


## Setup
```bash
git clone https://github.com/your-username/Automated_Financial_Intelligence_Engine.git
cd Automated_Financial_Intelligence_Engine
pip install -r requirements.txt
uvicorn main:app --reload