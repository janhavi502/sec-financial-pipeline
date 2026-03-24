import os
import snowflake.connector
from fastapi import APIRouter, HTTPException, Query
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()


def get_conn():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )


def run_query(sql: str) -> list[dict]:
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(sql)
    cols = [c[0].lower() for c in cursor.description]
    rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return rows


# ── Raw Staging ────────────────────────────────────────────────

@router.get("/raw/companies")
def get_raw_companies(limit: int = Query(50, le=500)):
    """Get list of companies from Raw Staging."""
    sql = f"""
        SELECT adsh, cik, name, sic, form, period, filed
        FROM SEC_FINANCIAL.RAW_STAGING.RAW_SUB
        WHERE name IS NOT NULL
        ORDER BY filed DESC
        LIMIT {limit}
    """
    return run_query(sql)


@router.get("/raw/stats")
def get_raw_stats():
    """Get row counts for all Raw Staging tables."""
    conn = get_conn()
    cursor = conn.cursor()
    stats = {}
    tables = ["RAW_SUB", "RAW_TAG", "RAW_NUM", "RAW_PRE"]
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM SEC_FINANCIAL.RAW_STAGING.{t}")
        stats[t] = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return stats


# ── JSON Transform ─────────────────────────────────────────────

@router.get("/json/filings")
def get_json_filings(limit: int = Query(50, le=500), form: str = None):
    """Get filings from JSON Transform table."""
    where = f"AND form = '{form}'" if form else ""
    sql = f"""
        SELECT adsh, cik, form, period, filed,
               payload:name::STRING AS company_name
        FROM SEC_FINANCIAL.JSON_TRANSFORM.FILING_JSON
        WHERE payload:name::STRING IS NOT NULL
        {where}
        ORDER BY filed DESC
        LIMIT {limit}
    """
    return run_query(sql)


@router.get("/json/company/{cik}")
def get_json_company(cik: int):
    """Get all filings for a specific company from JSON."""
    sql = f"""
        SELECT
            adsh,
            payload:name::STRING AS company_name,
            payload:form::STRING AS form_type,
            payload:fy::STRING AS fiscal_year,
            payload:fp::STRING AS fiscal_period,
            payload:period::STRING AS period_date
        FROM SEC_FINANCIAL.JSON_TRANSFORM.FILING_JSON
        WHERE cik = {cik}
        ORDER BY filed DESC
    """
    return run_query(sql)


# ── Fact Tables ────────────────────────────────────────────────

@router.get("/facts/balance-sheet")
def get_balance_sheet(
    limit: int = Query(50, le=500),
    form_type: str = None,
    fiscal_year: str = None
):
    """Get balance sheet facts with optional filters."""
    conditions = []
    if form_type:
        conditions.append(f"form_type = '{form_type}'")
    if fiscal_year:
        conditions.append(f"fiscal_year = '{fiscal_year}'")
    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    sql = f"""
        SELECT company_name, cik, fiscal_year, fiscal_period, form_type,
               assets_total, assets_current, liabilities_total,
               equity_total, cash_and_equivalents, long_term_debt
        FROM SEC_FINANCIAL.FACT_TABLES.BALANCE_SHEET_FACT
        {where}
        ORDER BY assets_total DESC NULLS LAST
        LIMIT {limit}
    """
    return run_query(sql)


@router.get("/facts/income-statement")
def get_income_statement(
    limit: int = Query(50, le=500),
    form_type: str = None,
    fiscal_year: str = None
):
    """Get income statement facts with optional filters."""
    conditions = []
    if form_type:
        conditions.append(f"form_type = '{form_type}'")
    if fiscal_year:
        conditions.append(f"fiscal_year = '{fiscal_year}'")
    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    sql = f"""
        SELECT company_name, cik, fiscal_year, fiscal_period, form_type,
               revenues, gross_profit, operating_income,
               net_income, eps_basic, eps_diluted
        FROM SEC_FINANCIAL.FACT_TABLES.INCOME_STATEMENT_FACT
        {where}
        ORDER BY revenues DESC NULLS LAST
        LIMIT {limit}
    """
    return run_query(sql)


@router.get("/facts/cash-flow")
def get_cash_flow(
    limit: int = Query(50, le=500),
    form_type: str = None
):
    """Get cash flow facts with optional filters."""
    where = f"WHERE form_type = '{form_type}'" if form_type else ""
    sql = f"""
        SELECT company_name, cik, fiscal_year, fiscal_period, form_type,
               cfo, cfi, cff, free_cash_flow, capex, net_change_in_cash
        FROM SEC_FINANCIAL.FACT_TABLES.CASH_FLOW_FACT
        {where}
        ORDER BY cfo DESC NULLS LAST
        LIMIT {limit}
    """
    return run_query(sql)


@router.get("/facts/top-companies")
def get_top_companies(metric: str = "assets_total", limit: int = 10):
    """Get top companies by a given metric from Balance Sheet."""
    allowed = ["assets_total", "equity_total", "cash_and_equivalents", "long_term_debt"]
    if metric not in allowed:
        raise HTTPException(400, f"Metric must be one of: {allowed}")
    sql = f"""
        SELECT company_name, cik, fiscal_year, {metric}
        FROM SEC_FINANCIAL.FACT_TABLES.BALANCE_SHEET_FACT
        WHERE {metric} IS NOT NULL AND form_type = '10-K'
        ORDER BY {metric} DESC
        LIMIT {limit}
    """
    return run_query(sql)