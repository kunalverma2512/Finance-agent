# 💰 Personal Finance Agent

An AI-powered personal finance management system that helps users **import transactions, categorize expenses, analyze spending, manage budgets and goals, detect unusual transactions, and receive financial insights**.

Built as a production-oriented backend using **FastAPI, PostgreSQL, SQLAlchemy, LangGraph, and Gemini**.

---

## 🚀 Features

* 🔐 User authentication with JWT
* 💳 Transaction management
* 📂 CSV transaction import
* ♻️ Duplicate transaction prevention
* 🏷️ Automatic expense categorization
* 📊 Spending and financial analytics
* 💰 Budget management
* 🎯 Financial goals
* 🚨 Anomaly / unusual spending detection
* 🤖 AI-powered financial insights
* 🧠 LangGraph-based agent workflow
* 📝 Audit logging
* ⚡ Rate limiting
* 🗄️ PostgreSQL database
* 🔄 Alembic database migrations
* 🧪 Automated tests
* 🐳 Docker support
* 🔁 CI workflow with GitHub Actions

---

## 🏗️ Architecture

```text
                         ┌─────────────────────┐
                         │     Frontend        │
                         │    HTML/CSS/JS      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      FastAPI        │
                         │      REST API       │
                         └──────────┬──────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
             ▼                      ▼                      ▼
      ┌─────────────┐       ┌──────────────┐       ┌─────────────┐
      │   Finance   │       │    Agent     │       │   Planning  │
      │   Services  │       │   Workflow   │       │   Services  │
      └──────┬──────┘       └──────┬───────┘       └──────┬──────┘
             │                     │                      │
             └─────────────────────┼──────────────────────┘
                                   ▼
                         ┌─────────────────────┐
                         │    PostgreSQL       │
                         │   SQLAlchemy ORM    │
                         └─────────────────────┘
                                   │
                         ┌─────────┴─────────┐
                         ▼                   ▼
                  ┌─────────────┐     ┌─────────────┐
                  │   Alembic   │     │   Audit /   │
                  │  Migrations │     │  Monitoring │
                  └─────────────┘     └─────────────┘

                         AI Layer
                            │
                            ▼
                    ┌───────────────┐
                    │   LangGraph   │
                    │ Agent Workflow │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Gemini / LLM   │
                    └───────────────┘
```

---

## 🧠 Agent Workflow

The agent uses a structured workflow instead of sending every request directly to an LLM.

```text
User Request
     │
     ▼
Request Router
     │
     ├── Transaction Analysis
     │
     ├── Budget Analysis
     │
     ├── Goal Planning
     │
     ├── Spending Insights
     │
     └── Financial Planning
             │
             ▼
        Finance Tools
             │
             ▼
        PostgreSQL
             │
             ▼
        Agent Response
```

This approach keeps financial operations **deterministic and database-backed**, while using the LLM where reasoning and natural-language generation are useful.

---

## 📂 CSV Import

The system supports importing financial transactions from CSV files.

Expected transaction data:

```csv
date,description,amount
2026-01-02,Netflix,-15.99
2026-01-03,Walmart,-84.50
2026-01-05,Salary,2500.00
2026-01-07,Uber,-18.25
```

The importer performs:

```text
CSV Upload
    ↓
File Validation
    ↓
Column Validation
    ↓
Data Normalization
    ↓
Duplicate Detection
    ↓
Transaction Storage
    ↓
Categorization
```

### Duplicate Protection

Re-importing the same transaction file does **not** create duplicate transactions.

The system identifies existing transactions before insertion and only persists new records.

Example:

```text
First import:
100 transactions → 100 inserted

Second import:
100 transactions → 0 duplicates created

Mixed import:
100 existing + 20 new
→ 20 inserted
→ 100 skipped
```

---

## 🛠️ Tech Stack

### Backend

* Python
* FastAPI
* SQLAlchemy
* PostgreSQL
* Alembic
* Pydantic

### AI / Agent

* LangGraph
* LangChain
* Gemini
* LLM-based financial insights

### Frontend

* HTML
* CSS
* JavaScript

### Testing & DevOps

* Pytest
* GitHub Actions
* Docker
* Docker Compose

---

## 📁 Project Structure

```text
personal-finance-agent/
│
├── app/
│   ├── agents/
│   │   ├── nodes/
│   │   ├── graph.py
│   │   ├── router.py
│   │   ├── render.py
│   │   └── state.py
│   │
│   ├── api/
│   │   └── routes/
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── logging.py
│   │   └── rate_limit.py
│   │
│   ├── db/
│   ├── integrations/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   ├── tools/
│   └── workers/
│
├── alembic/
│   └── versions/
│
├── frontend/
│   ├── css/
│   ├── js/
│   └── index.html
│
├── scripts/
├── tests/
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── alembic.ini
├── pytest.ini
└── README.md
```

---

## ⚙️ Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/personal-finance-agent.git
cd personal-finance-agent
```

### 2. Create virtual environment

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

For development:

```powershell
pip install -r requirements-dev.txt
```

### 4. Configure environment variables

Create a `.env` file:

```env
ENVIRONMENT=development
LOG_LEVEL=INFO

DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/finance

JWT_SECRET=your-secure-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
```

> Never commit `.env` or API keys to GitHub.

### 5. Run database migrations

```powershell
python -m alembic upgrade head
```

### 6. Start the API

```powershell
python -m uvicorn app.main:app --reload
```

API:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 🐳 Docker

Build and run the application:

```bash
docker compose up --build
```

Stop containers:

```bash
docker compose down
```

---

## 🧪 Testing

Run the complete test suite:

```powershell
pytest
```

The project includes tests for:

* Authentication
* Transactions
* CSV import
* Duplicate protection
* Categorization
* Budgets
* Goals
* Agent workflow
* Anomaly detection
* Finance engine
* User isolation
* Gemini integration

---

## 🔒 Security

The project includes several production-oriented security practices:

* JWT authentication
* Password hashing
* Environment-based secrets
* Database-backed user isolation
* API rate limiting
* Input validation
* File validation
* Audit logging
* Controlled agent tool access
* `.env` excluded from Git

---

## 🎯 Example Use Cases

### Import Transactions

```text
Upload bank CSV
      ↓
Validate transactions
      ↓
Detect duplicates
      ↓
Store in PostgreSQL
      ↓
Categorize expenses
```

### Ask the Agent

```text
"What did I spend the most on this month?"
```

```text
"How much did I spend on food?"
```

```text
"Are there any unusual transactions?"
```

```text
"How can I reduce my monthly expenses?"
```

```text
"Am I staying within my budget?"
```

The agent uses available financial data and tools before generating its response.

---

## 🧩 Engineering Principles

This project focuses on practical AI engineering rather than simply connecting an LLM to an API.

Key principles:

* **Database-first financial operations**
* **Deterministic tools for calculations**
* **LLM for reasoning and natural-language interaction**
* **Explicit agent workflow**
* **Input validation**
* **Error handling**
* **Observability and auditability**
* **User data isolation**
* **Automated testing**
* **Migration-based database management**
* **Container-ready deployment**

---

## 📌 Project Status

🚧 **Active Development**

Current capabilities include:

* Authentication
* PostgreSQL persistence
* Transaction management
* CSV import
* Duplicate prevention
* Categorization
* Budget and goal management
* Financial analytics
* Agent workflow
* Anomaly detection
* Automated tests
* Docker support
* CI workflow

Future improvements may include:

* Production cloud deployment
* Redis-based background jobs
* Advanced ML-based transaction classification
* Financial forecasting
* More integrations with financial data providers
* Improved agent memory
* Advanced monitoring and observability

---

## 👨‍💻 Author

**Kunal Verma**

Mathematics and Computing student at IIT (ISM) Dhanbad focused on:

* Data Science
* Machine Learning
* AI Engineering
* Agentic AI
* Production AI Systems

---

## ⭐ Why This Project?

Personal Finance Agent demonstrates how an AI application can combine:

**LLMs + Agentic Workflows + APIs + PostgreSQL + Security + Testing + Docker**

to solve a practical real-world problem.
