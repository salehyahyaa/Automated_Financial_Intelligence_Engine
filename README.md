# Automated Financial Intelligence Engine
A backend engine that securely ingests financial data from multiple institutions via plaid, centralizing all personal financial activity into a unified system. The platform applies statistical analysis and predictive modeling to generate portfolio insights, and integrates LLMs (Gemini) to enable natural language financial queries and personalized, datadriven intelligence on individual finances.



## Features
- Secure OAuth financial data ingestion
- Real time streaming ingestion
- Predictive Financial Modeling
- Automated Transaction Classification
- Portfolio performance analytics
- Quantitive timeseries forecasting (ARIMA / ML models)



## Project Structure
```
Automated_Financial_Intelligence_Engine/
├─ .gitignore
├─ LICENSE
├─ README.md
├─ requirements.txt
├─ db_architecture/
│  └─ schema_v1.sql
├─ documentation/
│  └─ plaid-python-master.zip
├─ src/
│  ├─ Backend/
│  │  ├─ Accounts.py
│  │  ├─ CheckingAccounts.py
│  │  ├─ CreditCards.py
│  │  ├─ DataAutomation.py
│  │  ├─ Endpoints.py
│  │  ├─ PlaidConnector.py
│  │  ├─ main.py
│  │  ├─ Analytics/
│  │  │  ├─ AnomalyDetector.py
│  │  │  ├─ PredictiveAnalytics.py
│  │  │  ├─ StatisticalAnalytics.py
│  │  │  └─ __init__.py
│  │  ├─ LLM/
│  │  │  ├─ client.py
│  │  │  ├─ prompts.py
│  │  │  └─ __init__.py
│  │  ├─ database/
│  │  │  ├─ Connection.py
│  │  │  └─ __init__.py
│  │  └─ __pycache__/
│  └─ Frontend/
│     ├─ chatbox.js
│     ├─ dashboard.css
│     ├─ dashboard.html
│     ├─ index.html
│     ├─ nav-drawer.js
│     ├─ plaid.js
│     └─ refresh.js
└─ tests/
```



## Installation
### 1. Clone the Repository
```
git clone https://github.com/salehyahyaa/Automated_Financial_Intelligence_Engine.git
cd Automated_Financial_Intelligence_Engine
```

### 2. Set Up Virtual Environment  
Create and activate a Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Required Dependencies  
Use the `requirements.txt` file to install all necessary Python libraries:

```
pip install -r requirements.txt
```



## How to Run

### 1. Create your `.env`
The backend loads env vars using `python-dotenv`, so make sure these exist before running:
```
# Plaid
PLAID_CLIENT_ID=...
PLAID_SECRET=...
PLAID_ENV=...
# Postgres
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=your_db_name
```

### 2. Run backend
From the repo root:
```
cd src/Backend
python3 main.py
```
Backend runs at:
- `http://127.0.0.1:5000`


### 3. Run frontend
In a new terminal:
```
cd src/Frontend
python3 -m http.server 8000
```

Open:
- `http://127.0.0.1:8000`


### 4. What to Expect
Once the application is running, you'll interact with a interface you will be to "connect your account". This component will allow you to secruly connect your finaincal instition(s). After successful connection(s) you will be able to see data across all your finaincal accounts and a chat box to input a question about your personal finances. The agents will debate the task and return a final answer after dynamically balancing between fast inference and more detailed reasoning.
