import os
import snowflake.connector
from fastapi import APIRouter, Query
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


@router.get("/company")
def search_company(name: str = Query(..., min_length=2)):
    """Search for a company by name across all storage approaches."""
    sql = f"""
        SELECT DISTINCT
            cik,
            name AS company_name,
            sic,
            form,
            period,
            filed
        FROM SEC_FINANCIAL.RAW_STAGING.RAW_SUB
        WHERE UPPER(name) LIKE UPPER('%{name}%')
        ORDER BY filed DESC
        LIMIT 20
    """
    return run_query(sql)


@router.get("/company/{cik}/financials")
def get_company_financials(cik: int):
    """Get complete financial summary for a company by CIK."""
    bs_sql = f"""
        SELECT 'Balance Sheet' AS statement,
               fiscal_year, fiscal_period, form_type,
               assets_total, liabilities_total, equity_total,
               cash_and_equivalents
        FROM SEC_FINANCIAL.FACT_TABLES.BALANCE_SHEET_FACT
        WHERE cik = {cik}
        ORDER BY filed_date DESC
        LIMIT 5
    """
    is_sql = f"""
        SELECT 'Income Statement' AS statement,
               fiscal_year, fiscal_period, form_type,
               revenues, gross_profit, net_income, eps_diluted
        FROM SEC_FINANCIAL.FACT_TABLES.INCOME_STATEMENT_FACT
        WHERE cik = {cik}
        ORDER BY filed_date DESC
        LIMIT 5
    """
    cf_sql = f"""
        SELECT 'Cash Flow' AS statement,
               fiscal_year, fiscal_period, form_type,
               cfo, cfi, cff, free_cash_flow
        FROM SEC_FINANCIAL.FACT_TABLES.CASH_FLOW_FACT
        WHERE cik = {cik}
        ORDER BY filed_date DESC
        LIMIT 5
    """
    return {
        "cik": cik,
        "balance_sheet": run_query(bs_sql),
        "income_statement": run_query(is_sql),
        "cash_flow": run_query(cf_sql),
    }