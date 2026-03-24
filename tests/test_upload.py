"""
test_upload.py
--------------
Post-upload tests to verify data integrity across all 3 storage approaches.
Tests:
    1. S3 — all 4 files exist and have content
    2. Raw Staging — row counts match expected
    3. JSON Transform — filing and tag counts correct
    4. Fact Tables — all 3 tables have data, no empty tables
"""

import os
import sys
import boto3
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME       = os.getenv("AWS_BUCKET_NAME")
AWS_REGION            = os.getenv("AWS_REGION")

SNOWFLAKE_ACCOUNT     = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER        = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD    = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_DATABASE    = os.getenv("SNOWFLAKE_DATABASE")
SNOWFLAKE_WAREHOUSE   = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_ROLE        = os.getenv("SNOWFLAKE_ROLE")

DATASET = "2024q4"

PASS = 0
FAIL = 0


def log(test_name: str, passed: bool, detail: str = ""):
    global PASS, FAIL
    status = "PASS" if passed else "FAIL"
    symbol = "✓" if passed else "✗"
    print(f"  [{status}] {symbol} {test_name}" + (f" — {detail}" if detail else ""))
    if passed:
        PASS += 1
    else:
        FAIL += 1


def get_snowflake_conn():
    return snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        database=SNOWFLAKE_DATABASE,
        warehouse=SNOWFLAKE_WAREHOUSE,
        role=SNOWFLAKE_ROLE,
    )


def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )


# ─────────────────────────────────────────────
# TEST SUITE 1: S3 Validation
# ─────────────────────────────────────────────
def test_s3():
    print("\n=== S3 Validation ===")
    s3 = get_s3_client()
    required_files = ["sub.txt", "tag.txt", "num.txt", "pre.txt"]

    for f in required_files:
        key = f"sec-data/{DATASET}/{f}"
        try:
            obj = s3.head_object(Bucket=AWS_BUCKET_NAME, Key=key)
            size = obj["ContentLength"]
            log(f"S3 file exists: {f}", True, f"{size:,} bytes")
        except Exception as e:
            log(f"S3 file exists: {f}", False, str(e))


# ─────────────────────────────────────────────
# TEST SUITE 2: Raw Staging
# ─────────────────────────────────────────────
def test_raw_staging():
    print("\n=== Raw Staging Validation ===")
    conn = get_snowflake_conn()
    cursor = conn.cursor()

    tables = {
        "RAW_STAGING.RAW_SUB": 6491,
        "RAW_STAGING.RAW_TAG": 84365,
        "RAW_STAGING.RAW_NUM": 3705078,
        "RAW_STAGING.RAW_PRE": 737504,
    }

    for table, expected in tables.items():
        try:
            cursor.execute(f"SELECT COUNT(*) FROM SEC_FINANCIAL.{table}")
            count = cursor.fetchone()[0]
            log(f"{table} row count", count == expected, f"{count:,} rows (expected {expected:,})")
        except Exception as e:
            log(f"{table} row count", False, str(e))

    # Test no nulls in key columns
    try:
        cursor.execute("SELECT COUNT(*) FROM SEC_FINANCIAL.RAW_STAGING.RAW_SUB WHERE adsh IS NULL")
        nulls = cursor.fetchone()[0]
        log("RAW_SUB adsh not null", nulls == 0, f"{nulls} null values found")
    except Exception as e:
        log("RAW_SUB adsh not null", False, str(e))

    try:
        cursor.execute("SELECT COUNT(*) FROM SEC_FINANCIAL.RAW_STAGING.RAW_SUB WHERE cik IS NULL")
        nulls = cursor.fetchone()[0]
        log("RAW_SUB cik not null", nulls == 0, f"{nulls} null values found")
    except Exception as e:
        log("RAW_SUB cik not null", False, str(e))

    cursor.close()
    conn.close()


# ─────────────────────────────────────────────
# TEST SUITE 3: JSON Transform
# ─────────────────────────────────────────────
def test_json_transform():
    print("\n=== JSON Transform Validation ===")
    conn = get_snowflake_conn()
    cursor = conn.cursor()

    # Check filing count
    try:
        cursor.execute("SELECT COUNT(*) FROM SEC_FINANCIAL.JSON_TRANSFORM.FILING_JSON")
        count = cursor.fetchone()[0]
        log("FILING_JSON row count", count == 6491, f"{count:,} filings")
    except Exception as e:
        log("FILING_JSON row count", False, str(e))

    # Check tag count
    try:
        cursor.execute("SELECT COUNT(*) FROM SEC_FINANCIAL.JSON_TRANSFORM.TAG_JSON")
        count = cursor.fetchone()[0]
        log("TAG_JSON row count", count >= 84365, f"{count:,} tags")
    except Exception as e:
        log("TAG_JSON row count", False, str(e))

    # Check payload is valid JSON
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM SEC_FINANCIAL.JSON_TRANSFORM.FILING_JSON
            WHERE payload IS NULL
        """)
        nulls = cursor.fetchone()[0]
        log("FILING_JSON payload not null", nulls == 0, f"{nulls} null payloads")
    except Exception as e:
        log("FILING_JSON payload not null", False, str(e))

    # Check we can query inside JSON
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM SEC_FINANCIAL.JSON_TRANSFORM.FILING_JSON
            WHERE payload:name::STRING IS NOT NULL
        """)
        count = cursor.fetchone()[0]
        log("FILING_JSON payload queryable", count > 0, f"{count:,} filings with company name")
    except Exception as e:
        log("FILING_JSON payload queryable", False, str(e))

    cursor.close()
    conn.close()


# ─────────────────────────────────────────────
# TEST SUITE 4: Fact Tables
# ─────────────────────────────────────────────
def test_fact_tables():
    print("\n=== Fact Tables Validation ===")
    conn = get_snowflake_conn()
    cursor = conn.cursor()

    tables = [
        "FACT_TABLES.BALANCE_SHEET_FACT",
        "FACT_TABLES.INCOME_STATEMENT_FACT",
        "FACT_TABLES.CASH_FLOW_FACT",
    ]

    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM SEC_FINANCIAL.{table}")
            count = cursor.fetchone()[0]
            log(f"{table} not empty", count > 0, f"{count:,} rows")
        except Exception as e:
            log(f"{table} not empty", False, str(e))

    # Check key metrics are populated
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM SEC_FINANCIAL.FACT_TABLES.BALANCE_SHEET_FACT
            WHERE assets_total IS NOT NULL
        """)
        count = cursor.fetchone()[0]
        log("Balance Sheet has assets data", count > 0, f"{count:,} filings with total assets")
    except Exception as e:
        log("Balance Sheet has assets data", False, str(e))

    try:
        cursor.execute("""
            SELECT COUNT(*) FROM SEC_FINANCIAL.FACT_TABLES.INCOME_STATEMENT_FACT
            WHERE net_income IS NOT NULL
        """)
        count = cursor.fetchone()[0]
        log("Income Statement has net income data", count > 0, f"{count:,} filings with net income")
    except Exception as e:
        log("Income Statement has net income data", False, str(e))

    try:
        cursor.execute("""
            SELECT COUNT(*) FROM SEC_FINANCIAL.FACT_TABLES.CASH_FLOW_FACT
            WHERE cfo IS NOT NULL
        """)
        count = cursor.fetchone()[0]
        log("Cash Flow has CFO data", count > 0, f"{count:,} filings with cash from operations")
    except Exception as e:
        log("Cash Flow has CFO data", False, str(e))

    cursor.close()
    conn.close()


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\nRunning post-upload tests for dataset: {DATASET}")
    print("=" * 50)

    test_s3()
    test_raw_staging()
    test_json_transform()
    test_fact_tables()

    print(f"\n{'=' * 50}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    print("=" * 50)

    if FAIL > 0:
        sys.exit(1)