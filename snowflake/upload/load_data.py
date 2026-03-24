"""
load_data.py
------------
Loads SEC financial statement data from S3 into Snowflake.
Handles all three storage approaches:
  1. Raw Staging  — loads TSV files as-is into RAW_STAGING tables
  2. JSON         — transforms and loads into FILING_JSON / TAG_JSON
  3. Fact Tables  — extracts key metrics into analytics-ready tables

Usage:
    python load_data.py --dataset 2024q4 --approach all
    python load_data.py --dataset 2024q4 --approach raw
    python load_data.py --dataset 2024q4 --approach json
    python load_data.py --dataset 2024q4 --approach facts
"""

import os
import io
import json
import argparse
import boto3
import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Config from .env
# ─────────────────────────────────────────────
AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME       = os.getenv("AWS_BUCKET_NAME")
AWS_REGION            = os.getenv("AWS_REGION")

SNOWFLAKE_ACCOUNT     = os.getenv("SNOWFLAKE_ACCOUNT")   # e.g. abc123.us-east-1
SNOWFLAKE_USER        = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD    = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_DATABASE    = os.getenv("SNOWFLAKE_DATABASE", "SEC_FINANCIAL_DB")
SNOWFLAKE_WAREHOUSE   = os.getenv("SNOWFLAKE_WAREHOUSE", "SEC_WH")
SNOWFLAKE_ROLE        = os.getenv("SNOWFLAKE_ROLE", "SYSADMIN")

# ─────────────────────────────────────────────
# XBRL tag → fact table column mapping
# Maps standard SEC XBRL tag names to our fact table columns
# ─────────────────────────────────────────────

BALANCE_SHEET_TAG_MAP = {
    "Assets":                                   "assets_total",
    "AssetsCurrent":                            "assets_current",
    "CashAndCashEquivalentsAtCarryingValue":     "cash_and_equivalents",
    "ReceivablesNetCurrent":                     "receivables",
    "InventoryNet":                              "inventory",
    "AssetsNoncurrent":                         "assets_noncurrent",
    "PropertyPlantAndEquipmentNet":              "ppe_net",
    "Goodwill":                                 "goodwill",
    "FiniteLivedIntangibleAssetsNet":            "intangible_assets",
    "Liabilities":                              "liabilities_total",
    "LiabilitiesCurrent":                       "liabilities_current",
    "AccountsPayableCurrent":                   "accounts_payable",
    "ShortTermBorrowings":                      "short_term_debt",
    "LiabilitiesNoncurrent":                    "liabilities_noncurrent",
    "LongTermDebt":                             "long_term_debt",
    "StockholdersEquity":                       "equity_total",
    "RetainedEarningsAccumulatedDeficit":        "retained_earnings",
    "CommonStockValue":                         "common_stock",
}

INCOME_STATEMENT_TAG_MAP = {
    "Revenues":                                 "revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax": "revenues",
    "CostOfRevenue":                            "cost_of_revenue",
    "GrossProfit":                              "gross_profit",
    "OperatingExpenses":                        "operating_expenses",
    "ResearchAndDevelopmentExpense":            "research_and_development",
    "SellingGeneralAndAdministrativeExpense":   "selling_general_admin",
    "OperatingIncomeLoss":                      "operating_income",
    "InterestExpense":                          "interest_expense",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest": "income_before_tax",
    "IncomeTaxExpenseBenefit":                  "income_tax_expense",
    "NetIncomeLoss":                            "net_income",
    "EarningsPerShareBasic":                    "eps_basic",
    "EarningsPerShareDiluted":                  "eps_diluted",
    "WeightedAverageNumberOfSharesOutstandingBasic": "shares_outstanding",
}

CASH_FLOW_TAG_MAP = {
    "NetCashProvidedByUsedInOperatingActivities":  "cfo",
    "NetIncomeLoss":                               "net_income_cf",
    "DepreciationDepletionAndAmortization":        "depreciation_amortization",
    "IncreaseDecreaseInOperatingCapital":          "changes_in_working_capital",
    "NetCashProvidedByUsedInInvestingActivities":  "cfi",
    "PaymentsToAcquirePropertyPlantAndEquipment":  "capex",
    "PaymentsToAcquireBusinessesNetOfCashAcquired": "acquisitions",
    "NetCashProvidedByUsedInFinancingActivities":  "cff",
    "PaymentsOfDividends":                         "dividends_paid",
    "RepaymentsOfDebt":                            "debt_repayment",
    "PaymentsForRepurchaseOfCommonStock":          "share_repurchases",
    "CashAndCashEquivalentsPeriodIncreaseDecrease": "net_change_in_cash",
    "CashAndCashEquivalentsAtCarryingValue":       "cash_end_of_period",
}

# Statement type codes from PRE table
STMT_MAP = {
    "BS": "Balance Sheet",
    "IS": "Income Statement",
    "CF": "Cash Flow",
    "EQ": "Equity",
    "CI": "Comprehensive Income",
}


# ─────────────────────────────────────────────
# S3 Helper
# ─────────────────────────────────────────────

def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )


def read_tsv_from_s3(dataset: str, filename: str) -> pd.DataFrame:
    """
    Read a TSV file from S3 and return as a DataFrame.
    Path format: sec-data/{dataset}/{filename}
    """
    s3 = get_s3_client()
    key = f"sec-data/{dataset}/{filename}"
    print(f"  Reading s3://{AWS_BUCKET_NAME}/{key}")

    obj = s3.get_object(Bucket=AWS_BUCKET_NAME, Key=key)
    content = obj["Body"].read()

    # SEC files use tab separator and latin-1 encoding
    df = pd.read_csv(
        io.BytesIO(content),
        sep="\t",
        encoding="latin-1",
        low_memory=False,
        dtype=str,          # Read everything as string first — we cast later
    )
    # Normalize column names to uppercase
    df.columns = [c.upper() for c in df.columns]
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df


# ─────────────────────────────────────────────
# Snowflake Helper
# ─────────────────────────────────────────────

def get_snowflake_connection(schema: str):
    """Return a Snowflake connection set to the given schema."""
    conn = snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        database=SNOWFLAKE_DATABASE,
        schema=schema,
        warehouse=SNOWFLAKE_WAREHOUSE,
        role=SNOWFLAKE_ROLE,
    )
    return conn


def run_sql(conn, sql: str):
    """Execute a SQL statement."""
    cursor = conn.cursor()
    cursor.execute(sql)
    cursor.close()


# ─────────────────────────────────────────────
# APPROACH 1: Raw Staging
# ─────────────────────────────────────────────

def load_raw_staging(dataset: str):
    """
    Load all 4 TSV files from S3 directly into RAW_STAGING tables.
    No transformation — pure copy.
    """
    print(f"\n{'='*60}")
    print(f"APPROACH 1: Loading Raw Staging for {dataset}")
    print(f"{'='*60}")

    # Map of S3 filename → Snowflake table name
    files = {
        "sub.txt": "RAW_SUB",
        "tag.txt": "RAW_TAG",
        "num.txt": "RAW_NUM",
        "pre.txt": "RAW_PRE",
    }

    conn = get_snowflake_connection("RAW_STAGING")

    for filename, table in files.items():
        print(f"\nLoading {filename} → {table}...")
        df = read_tsv_from_s3(dataset, filename)

        # write_pandas uses the DataFrame column names to match table columns
        # success = True/False, nchunks = number of chunks written, nrows = rows written
        success, nchunks, nrows, _ = write_pandas(
            conn=conn,
            df=df,
            table_name=table,
            schema="RAW_STAGING",
            database=SNOWFLAKE_DATABASE,
            auto_create_table=False,    # We already created the table via SQL
            overwrite=False,            # Append mode — set True to replace
        )

        if success:
            print(f"  ✓ Loaded {nrows:,} rows into {table} ({nchunks} chunks)")
        else:
            print(f"  ✗ Failed to load {table}")

    conn.close()
    print("\nRaw staging complete!")


# ─────────────────────────────────────────────
# APPROACH 2: JSON Transformation
# ─────────────────────────────────────────────

def load_json_transform(dataset: str):
    """
    Build JSON payloads and load into FILING_JSON and TAG_JSON.
    Uses write_pandas for bulk inserts — same approach as raw staging.
    """
    print(f"\n{'='*60}")
    print(f"APPROACH 2: Loading JSON Transform for {dataset}")
    print(f"{'='*60}")

    print("\nReading source files from S3...")
    sub = read_tsv_from_s3(dataset, "sub.txt")
    num = read_tsv_from_s3(dataset, "num.txt")
    pre = read_tsv_from_s3(dataset, "pre.txt")
    tag = read_tsv_from_s3(dataset, "tag.txt")

    conn = get_snowflake_connection("JSON_TRANSFORM")
    cursor = conn.cursor()

    # ── Step 1: Load TAG_JSON ──────────────────────────────────
    print("\nBuilding TAG_JSON records...")

    # Store payload as string — we'll convert to VARIANT via SQL after
    tag_df = pd.DataFrame({
        "TAG":     tag["TAG"].astype(str),
        "VERSION": tag["VERSION"].astype(str),
        "PAYLOAD": tag.apply(lambda r: json.dumps({
            "tag":      r.get("TAG"),
            "version":  r.get("VERSION"),
            "custom":   r.get("CUSTOM"),
            "abstract": r.get("ABSTRACT"),
            "datatype": r.get("DATATYPE"),
            "iord":     r.get("IORD"),
            "crdr":     r.get("CRDR"),
            "tlabel":   r.get("TLABEL"),
            "doc":      r.get("DOC"),
        }), axis=1)
    })

    # Write to a temp staging table first
    cursor.execute("CREATE OR REPLACE TEMP TABLE TAG_JSON_STAGE (TAG VARCHAR, VERSION VARCHAR, PAYLOAD VARCHAR)")
    write_pandas(conn, tag_df, "TAG_JSON_STAGE", auto_create_table=False)

    # Then insert into real table with PARSE_JSON
    cursor.execute("""
        INSERT INTO JSON_TRANSFORM.TAG_JSON (tag, version, payload)
        SELECT TAG, VERSION, PARSE_JSON(PAYLOAD) FROM TAG_JSON_STAGE
    """)
    conn.commit()
    print(f"  ✓ Loaded {len(tag_df):,} tags into TAG_JSON")

    # ── Step 2: Build PRE lookup ───────────────────────────────
    print("\nBuilding PRE lookup...")
    pre_lookup = {}
    for _, row in pre.iterrows():
        adsh = row.get("ADSH", "")
        if adsh not in pre_lookup:
            pre_lookup[adsh] = {}
        pre_lookup[adsh][str(row.get("TAG", ""))] = row.get("STMT", "")

    # ── Step 3: Group NUM by adsh ──────────────────────────────
    print("Grouping NUM by filing...")
    num_by_adsh = {}
    for _, row in num.iterrows():
        adsh = row.get("ADSH", "")
        if adsh not in num_by_adsh:
            num_by_adsh[adsh] = []
        val = row.get("VALUE")
        try:
            val = float(val) if val and str(val) != "nan" else None
        except (ValueError, TypeError):
            val = None
        num_by_adsh[adsh].append({
            "tag":   str(row.get("TAG", "")),
            "ddate": row.get("DDATE"),
            "uom":   row.get("UOM"),
            "value": val,
        })

    # ── Step 4: Build FILING_JSON records ─────────────────────
    print(f"\nBuilding {len(sub):,} filing JSON records...")

    def safe_int(v):
        try:
            return int(v) if v and str(v) != "nan" else None
        except (ValueError, TypeError):
            return None

    rows = []
    for _, sub_row in sub.iterrows():
        adsh = sub_row.get("ADSH", "")
        if not adsh:
            continue

        stmt_lookup = pre_lookup.get(adsh, {})
        facts = [
            {**f, "stmt": stmt_lookup.get(f["tag"], "")}
            for f in num_by_adsh.get(adsh, [])
        ]

        rows.append({
            "ADSH":    adsh,
            "CIK":     safe_int(sub_row.get("CIK")),
            "FORM":    sub_row.get("FORM"),
            "PERIOD":  safe_int(sub_row.get("PERIOD")),
            "FILED":   safe_int(sub_row.get("FILED")),
            "PAYLOAD": json.dumps({
                "adsh":   adsh,
                "cik":    sub_row.get("CIK"),
                "name":   sub_row.get("NAME"),
                "form":   sub_row.get("FORM"),
                "period": sub_row.get("PERIOD"),
                "filed":  sub_row.get("FILED"),
                "fy":     sub_row.get("FY"),
                "fp":     sub_row.get("FP"),
                "sic":    sub_row.get("SIC"),
                "facts":  facts,
            })
        })

    filing_df = pd.DataFrame(rows)
    print(f"Built {len(filing_df):,} filing records, uploading to Snowflake...")

    # Write to temp staging table
    cursor.execute("""
        CREATE OR REPLACE TEMP TABLE FILING_JSON_STAGE (
            ADSH VARCHAR, CIK NUMBER, FORM VARCHAR,
            PERIOD NUMBER, FILED NUMBER, PAYLOAD VARCHAR
        )
    """)
    write_pandas(conn, filing_df, "FILING_JSON_STAGE", auto_create_table=False)

    # Insert into real table with PARSE_JSON
    cursor.execute("""
        INSERT INTO JSON_TRANSFORM.FILING_JSON
            (adsh, cik, form, period, filed, payload)
        SELECT ADSH, CIK, FORM, PERIOD, FILED, PARSE_JSON(PAYLOAD)
        FROM FILING_JSON_STAGE
    """)
    conn.commit()

    cursor.close()
    conn.close()
    print(f"  ✓ Total FILING_JSON records loaded: {len(filing_df):,}")
    print("\nJSON transform complete!")
# ─────────────────────────────────────────────
# APPROACH 3: Denormalized Fact Tables
# ─────────────────────────────────────────────

def extract_fact_value(num_df: pd.DataFrame, adsh: str, tag_map: dict) -> dict:
    """
    For a given filing (adsh), scan the NUM table and extract
    the values for each tag in tag_map.
    Returns a dict of {column_name: value}.
    """
    result = {}
    filing_nums = num_df[num_df["ADSH"] == adsh]

    for xbrl_tag, col_name in tag_map.items():
        # Find rows matching this tag (take the one with largest ddate = most recent)
        matches = filing_nums[filing_nums["TAG"] == xbrl_tag]
        if not matches.empty:
            # Prefer the row with the most recent ddate
            row = matches.loc[matches["DDATE"].idxmax()]
            val = row.get("VALUE")
            try:
                result[col_name] = float(val) if val and str(val) != "nan" else None
            except (ValueError, TypeError):
                result[col_name] = None
        else:
            if col_name not in result:  # Don't overwrite if another tag already filled it
                result[col_name] = None

    return result


def load_fact_tables(dataset: str):
    print(f"\n{'='*60}")
    print(f"APPROACH 3: Loading Fact Tables for {dataset}")
    print(f"{'='*60}")

    import os

    BS_CACHE = "/tmp/bs_rows.csv"
    IS_CACHE = "/tmp/is_rows.csv"
    CF_CACHE = "/tmp/cf_rows.csv"

    # ── Step 1: Process or load from cache ────────────────────
    if os.path.exists(BS_CACHE) and os.path.exists(IS_CACHE) and os.path.exists(CF_CACHE):
        print("\nLoading from CSV cache (skipping reprocessing)...")
        bs_df = pd.read_csv(BS_CACHE, dtype=str)
        is_df = pd.read_csv(IS_CACHE, dtype=str)
        cf_df = pd.read_csv(CF_CACHE, dtype=str)
        print(f"  Loaded {len(bs_df):,} BS, {len(is_df):,} IS, {len(cf_df):,} CF rows from cache")
    else:
        print("\nReading source files from S3...")
        sub = read_tsv_from_s3(dataset, "sub.txt")
        num = read_tsv_from_s3(dataset, "num.txt")

        bs_rows, is_rows, cf_rows = [], [], []

        print(f"\nProcessing {len(sub):,} filings...")
        for i, (_, sub_row) in enumerate(sub.iterrows()):
            adsh = sub_row.get("ADSH", "")
            if not adsh:
                continue

            def safe_int(v):
                try:
                    return int(float(v)) if v and str(v) not in ("nan", "None", "") else None
                except (ValueError, TypeError):
                    return None

            common = {
                "ADSH":          adsh,
                "CIK":           safe_int(sub_row.get("CIK")),
                "COMPANY_NAME":  str(sub_row.get("NAME", "") or ""),
                "TICKER":        None,
                "SIC":           safe_int(sub_row.get("SIC")),
                "PERIOD_DATE":   safe_int(sub_row.get("PERIOD")) or 0,
                "FISCAL_YEAR":   str(sub_row.get("FY", "") or "")[:4] or "N/A",
                "FISCAL_PERIOD": str(sub_row.get("FP", "") or "")[:2] or "NA",
                "FILED_DATE":    safe_int(sub_row.get("FILED")),
                "FORM_TYPE":     str(sub_row.get("FORM", "") or ""),
            }

            bs_facts  = extract_fact_value(num, adsh, BALANCE_SHEET_TAG_MAP)
            is_facts  = extract_fact_value(num, adsh, INCOME_STATEMENT_TAG_MAP)
            cf_facts  = extract_fact_value(num, adsh, CASH_FLOW_TAG_MAP)

            cfo   = cf_facts.get("cfo")
            capex = cf_facts.get("capex")
            cf_facts["free_cash_flow"] = (
                (cfo or 0) + (capex or 0) if cfo is not None else None
            )

            bs_rows.append({**common, **{k.upper(): v for k, v in bs_facts.items()}})
            is_rows.append({**common, **{k.upper(): v for k, v in is_facts.items()}})
            cf_rows.append({**common, **{k.upper(): v for k, v in cf_facts.items()}})

            if (i + 1) % 200 == 0:
                print(f"  ... processed {i+1:,} filings")

        bs_df = pd.DataFrame(bs_rows)
        is_df = pd.DataFrame(is_rows)
        cf_df = pd.DataFrame(cf_rows)

        print("\nSaving to CSV cache...")
        bs_df.to_csv(BS_CACHE, index=False)
        is_df.to_csv(IS_CACHE, index=False)
        cf_df.to_csv(CF_CACHE, index=False)
        print("Saved!")

    # ── Step 2: Define columns ─────────────────────────────────
    bs_cols = [
        "ADSH","CIK","COMPANY_NAME","TICKER","SIC","PERIOD_DATE","FISCAL_YEAR",
        "FISCAL_PERIOD","FILED_DATE","FORM_TYPE","ASSETS_TOTAL","ASSETS_CURRENT",
        "CASH_AND_EQUIVALENTS","RECEIVABLES","INVENTORY","ASSETS_NONCURRENT",
        "PPE_NET","GOODWILL","INTANGIBLE_ASSETS","LIABILITIES_TOTAL",
        "LIABILITIES_CURRENT","ACCOUNTS_PAYABLE","SHORT_TERM_DEBT",
        "LIABILITIES_NONCURRENT","LONG_TERM_DEBT","EQUITY_TOTAL",
        "RETAINED_EARNINGS","COMMON_STOCK",
    ]
    is_cols = [
        "ADSH","CIK","COMPANY_NAME","TICKER","SIC","PERIOD_DATE","FISCAL_YEAR",
        "FISCAL_PERIOD","FILED_DATE","FORM_TYPE","REVENUES","COST_OF_REVENUE",
        "GROSS_PROFIT","OPERATING_EXPENSES","RESEARCH_AND_DEVELOPMENT",
        "SELLING_GENERAL_ADMIN","OPERATING_INCOME","INTEREST_EXPENSE",
        "INCOME_BEFORE_TAX","INCOME_TAX_EXPENSE","NET_INCOME","EPS_BASIC",
        "EPS_DILUTED","SHARES_OUTSTANDING",
    ]
    cf_cols = [
        "ADSH","CIK","COMPANY_NAME","TICKER","SIC","PERIOD_DATE","FISCAL_YEAR",
        "FISCAL_PERIOD","FILED_DATE","FORM_TYPE","CFO","NET_INCOME_CF",
        "DEPRECIATION_AMORTIZATION","CHANGES_IN_WORKING_CAPITAL","CFI","CAPEX",
        "ACQUISITIONS","CFF","DIVIDENDS_PAID","DEBT_REPAYMENT","SHARE_REPURCHASES",
        "NET_CHANGE_IN_CASH","CASH_END_OF_PERIOD","FREE_CASH_FLOW",
    ]

    def prep_df(df: pd.DataFrame, cols: list) -> pd.DataFrame:
        df = df.copy()
        # Add missing columns
        for col in cols:
            if col not in df.columns:
                df[col] = None
        df = df[cols]
        # Fix string columns
        df["FISCAL_YEAR"]   = df["FISCAL_YEAR"].fillna("N/A").astype(str).str[:4]
        df["FISCAL_PERIOD"] = df["FISCAL_PERIOD"].fillna("NA").astype(str).str[:2]
        df["PERIOD_DATE"]   = pd.to_numeric(df["PERIOD_DATE"], errors="coerce").fillna(0).astype(int)
        return df

    # ── Step 3: Insert into Snowflake ─────────────────────────
    def insert_df_to_snowflake(df: pd.DataFrame, table: str, cols: list):
        conn = get_snowflake_connection("FACT_TABLES")
        cursor = conn.cursor()
        df = prep_df(df, cols)

        col_str = ", ".join(cols)
        placeholders = ", ".join(["%s"] * len(cols))
        sql = f"INSERT INTO {table} ({col_str}) VALUES ({placeholders})"

        total = 0
        for _, row in df.iterrows():
            values = []
            for v in row:
                if v is None or (isinstance(v, float) and v != v):
                    values.append(None)
                elif str(v) in ("nan", "None", ""):
                    values.append(None)
                else:
                    values.append(v)
            cursor.execute(sql, values)
            total += 1
            if total % 500 == 0:
                conn.commit()
                print(f"  ... {total:,} / {len(df):,} rows inserted")

        conn.commit()
        cursor.close()
        conn.close()
        return total

    print("\nWriting Balance Sheet facts to Snowflake...")
    n = insert_df_to_snowflake(bs_df, "FACT_TABLES.BALANCE_SHEET_FACT", bs_cols)
    print(f"  ✓ {n:,} rows → BALANCE_SHEET_FACT")

    print("\nWriting Income Statement facts to Snowflake...")
    n = insert_df_to_snowflake(is_df, "FACT_TABLES.INCOME_STATEMENT_FACT", is_cols)
    print(f"  ✓ {n:,} rows → INCOME_STATEMENT_FACT")

    print("\nWriting Cash Flow facts to Snowflake...")
    n = insert_df_to_snowflake(cf_df, "FACT_TABLES.CASH_FLOW_FACT", cf_cols)
    print(f"  ✓ {n:,} rows → CASH_FLOW_FACT")

    print("\nFact tables complete!")
# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Load SEC data from S3 into Snowflake")
    parser.add_argument(
        "--dataset", default="2024q4",
        help="Dataset name, e.g. 2024q4 (default: 2024q4)"
    )
    parser.add_argument(
        "--approach", default="all",
        choices=["all", "raw", "json", "facts"],
        help="Which storage approach to load (default: all)"
    )
    args = parser.parse_args()

    print(f"\nLoading dataset: {args.dataset}")
    print(f"Approach: {args.approach}")

    if args.approach in ("all", "raw"):
        load_raw_staging(args.dataset)

    if args.approach in ("all", "json"):
        load_json_transform(args.dataset)

    if args.approach in ("all", "facts"):
        load_fact_tables(args.dataset)

    print("\n✓ All done!")


if __name__ == "__main__":
    main()