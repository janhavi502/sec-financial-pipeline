# SEC Financial Intelligence Pipeline

A production-grade financial data pipeline that ingests SEC EDGAR quarterly datasets, stores data across three Snowflake storage strategies, validates with DBT, automates with Airflow, and serves through a FastAPI + Streamlit interface.

---

## Architecture

```
SEC EDGAR Website
        ↓
    AWS S3 (Raw Storage)
        ↓
┌───────────────────────────────┐
│         Snowflake             │
│  ┌─────────────────────────┐  │
│  │   RAW_STAGING           │  │
│  │   JSON_TRANSFORM        │  │
│  │   FACT_TABLES           │  │
│  └─────────────────────────┘  │
└───────────────────────────────┘
        ↓
    DBT (Quality & Tests)
        ↓
    Airflow (Orchestration)
        ↓
  FastAPI + Streamlit (UI)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data Source | SEC EDGAR Financial Statement Datasets |
| Ingestion | Python, requests, BeautifulSoup |
| Cloud Storage | AWS S3 |
| Data Warehouse | Snowflake |
| Transformation | DBT (dbt-snowflake) |
| Orchestration | Apache Airflow |
| Backend API | FastAPI, SQLAlchemy |
| Frontend | Streamlit |
| Containerization | Docker, Docker Compose |

---

## Storage Approaches

### 1. Raw Staging
Loads all 4 SEC TSV files as-is into Snowflake with no transformation.

| Table | Rows |
|---|---|
| RAW_SUB | 6,491 |
| RAW_TAG | 84,365 |
| RAW_NUM | 3,705,078 |
| RAW_PRE | 737,504 |

### 2. JSON Transform
Converts each filing into a nested JSON object stored in a Snowflake VARIANT column — flexible querying without rigid schema.

### 3. Denormalized Fact Tables
Extracts key financial metrics into 3 analytics-ready tables:
- **BALANCE_SHEET_FACT** — Assets, liabilities, equity
- **INCOME_STATEMENT_FACT** — Revenue, profit, EPS
- **CASH_FLOW_FACT** — CFO, CFI, CFF, Free Cash Flow

---

## Project Structure

```
sec-financial-pipeline/
├── scraper/
│   └── sec_scraper.py          # SEC data scraping + S3 upload
├── snowflake/
│   ├── schemas/                # SQL for all 3 storage approaches
│   └── upload/
│       └── load_data.py        # Data loading scripts
├── dbt/
│   └── sec_pipeline/           # DBT project
│       └── models/staging/     # Staging models + tests
├── airflow/
│   ├── dags/                   # 3 Airflow DAGs
│   └── docker-compose.yml      # Airflow Docker setup
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── routers/
│   │   ├── financial_router.py
│   │   └── search_router.py
│   └── Dockerfile
├── frontend/
│   ├── app.py                  # Streamlit UI
│   └── Dockerfile
├── tests/
│   └── test_upload.py          # 20 post-upload tests
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Setup & Installation

### Prerequisites
- Docker Desktop
- AWS account (free tier)
- Snowflake account (free trial)

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/sec-financial-pipeline.git
cd sec-financial-pipeline
```

### 2. Configure environment variables
```bash
cp .env.example .env
```

Fill in `.env`:
```
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=SEC_FINANCIAL
SNOWFLAKE_WAREHOUSE=SEC_WAREHOUSE
SNOWFLAKE_ROLE=ACCOUNTADMIN

AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_BUCKET_NAME=sec-financial-pipeline
AWS_REGION=us-east-2
```

### 3. Run with Docker
```bash
docker-compose up --build
```

### 4. Access the application

| Service | URL |
|---|---|
| Streamlit UI | http://localhost:8501 |
| FastAPI Docs | http://localhost:8000/docs |
| Airflow UI | http://localhost:8080 |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/financial/raw/companies` | List companies from Raw Staging |
| GET | `/financial/raw/stats` | Row counts for all raw tables |
| GET | `/financial/json/filings` | Filings from JSON Transform |
| GET | `/financial/facts/balance-sheet` | Balance sheet facts |
| GET | `/financial/facts/income-statement` | Income statement facts |
| GET | `/financial/facts/cash-flow` | Cash flow facts |
| GET | `/financial/facts/top-companies` | Top companies by metric |
| GET | `/search/company` | Search company by name |
| GET | `/search/company/{cik}/financials` | Full financials by CIK |

---

## Testing

Run post-upload tests:
```bash
python tests/test_upload.py
```

Expected output: **20 passed, 0 failed**

---

## Storage Approach Comparison

| Approach | Pros | Cons |
|---|---|---|
| Raw Staging | Simple, no transformation, full fidelity | Hard to query, no types |
| JSON Transform | Flexible schema, easy nesting | Slower queries, larger storage |
| Fact Tables | Fast queries, analytics-ready | Schema changes require migration |

---

## AI Use Disclosure

See [AIUseDisclosure.md](./AIUseDisclosure.md)