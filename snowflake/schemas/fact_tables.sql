-- =============================================================
-- DENORMALIZED FACT TABLES SCHEMA
-- Three analytics-ready tables: Balance Sheet, Income Statement,
-- Cash Flow. Each row = one company, one period, key metrics.
-- Easy for analysts — no joins needed.
-- =============================================================

USE DATABASE SEC_FINANCIAL;
USE SCHEMA FACT_TABLES;

-- -------------------------------------------------------------
-- 1. BALANCE_SHEET_FACT
--    Key balance sheet metrics per company per period
-- -------------------------------------------------------------
CREATE OR REPLACE TABLE BALANCE_SHEET_FACT (
    -- Identifiers
    adsh                        VARCHAR(20),    -- Filing accession number
    cik                         NUMBER(10)  NOT NULL,
    company_name                VARCHAR(150),
    ticker                      VARCHAR(10),    -- Populated later via CIK lookup
    sic                         NUMBER(4),      -- Industry code

    -- Period info
    period_date                 NUMBER(8),      -- Balance sheet date YYYYMMDD
    fiscal_year                 VARCHAR(4),
    fiscal_period               VARCHAR(2),     -- Q1, Q2, Q3, FY
    filed_date                  NUMBER(8),
    form_type                   VARCHAR(10),    -- 10-K or 10-Q

    -- Assets
    assets_total                FLOAT,          -- Total Assets
    assets_current              FLOAT,          -- Current Assets
    cash_and_equivalents        FLOAT,          -- Cash and Cash Equivalents
    receivables                 FLOAT,          -- Net Receivables
    inventory                   FLOAT,          -- Inventory
    assets_noncurrent           FLOAT,          -- Non-current Assets
    ppe_net                     FLOAT,          -- Property Plant Equipment Net
    goodwill                    FLOAT,          -- Goodwill
    intangible_assets           FLOAT,          -- Intangible Assets

    -- Liabilities
    liabilities_total           FLOAT,          -- Total Liabilities
    liabilities_current         FLOAT,          -- Current Liabilities
    accounts_payable            FLOAT,          -- Accounts Payable
    short_term_debt             FLOAT,          -- Short Term Debt
    liabilities_noncurrent      FLOAT,          -- Non-current Liabilities
    long_term_debt              FLOAT,          -- Long Term Debt

    -- Equity
    equity_total                FLOAT,          -- Stockholders Equity
    retained_earnings           FLOAT,          -- Retained Earnings
    common_stock                FLOAT,          -- Common Stock

    -- Metadata
    created_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (cik, period_date, fiscal_year, fiscal_period)
);

-- -------------------------------------------------------------
-- 2. INCOME_STATEMENT_FACT
--    Key income statement metrics per company per period
-- -------------------------------------------------------------
CREATE OR REPLACE TABLE INCOME_STATEMENT_FACT (
    -- Identifiers
    adsh                        VARCHAR(20),
    cik                         NUMBER(10)  NOT NULL,
    company_name                VARCHAR(150),
    ticker                      VARCHAR(10),
    sic                         NUMBER(4),

    -- Period info
    period_date                 NUMBER(8),
    fiscal_year                 VARCHAR(4),
    fiscal_period               VARCHAR(2),
    filed_date                  NUMBER(8),
    form_type                   VARCHAR(10),

    -- Revenue
    revenues                    FLOAT,          -- Total Revenues
    cost_of_revenue             FLOAT,          -- Cost of Revenue / COGS
    gross_profit                FLOAT,          -- Gross Profit

    -- Operating
    operating_expenses          FLOAT,          -- Total Operating Expenses
    research_and_development    FLOAT,          -- R&D Expense
    selling_general_admin       FLOAT,          -- SG&A Expense
    operating_income            FLOAT,          -- Operating Income / EBIT

    -- Below the line
    interest_expense            FLOAT,          -- Interest Expense
    income_before_tax           FLOAT,          -- Income Before Tax
    income_tax_expense          FLOAT,          -- Income Tax Expense
    net_income                  FLOAT,          -- Net Income

    -- Per share
    eps_basic                   FLOAT,          -- Earnings Per Share Basic
    eps_diluted                 FLOAT,          -- Earnings Per Share Diluted
    shares_outstanding          FLOAT,          -- Weighted Average Shares

    -- Metadata
    created_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (cik, period_date, fiscal_year, fiscal_period)
);

-- -------------------------------------------------------------
-- 3. CASH_FLOW_FACT
--    Key cash flow metrics per company per period
-- -------------------------------------------------------------
CREATE OR REPLACE TABLE CASH_FLOW_FACT (
    -- Identifiers
    adsh                        VARCHAR(20),
    cik                         NUMBER(10)  NOT NULL,
    company_name                VARCHAR(150),
    ticker                      VARCHAR(10),
    sic                         NUMBER(4),

    -- Period info
    period_date                 NUMBER(8),
    fiscal_year                 VARCHAR(4),
    fiscal_period               VARCHAR(2),
    filed_date                  NUMBER(8),
    form_type                   VARCHAR(10),

    -- Operating Activities
    cfo                         FLOAT,          -- Cash from Operations
    net_income_cf               FLOAT,          -- Net Income (in CF statement)
    depreciation_amortization   FLOAT,          -- D&A (non-cash add-back)
    changes_in_working_capital  FLOAT,          -- Working Capital Changes

    -- Investing Activities
    cfi                         FLOAT,          -- Cash from Investing
    capex                       FLOAT,          -- Capital Expenditures (negative)
    acquisitions                FLOAT,          -- Acquisitions

    -- Financing Activities
    cff                         FLOAT,          -- Cash from Financing
    dividends_paid              FLOAT,          -- Dividends Paid
    debt_repayment              FLOAT,          -- Debt Repayments
    share_repurchases           FLOAT,          -- Share Buybacks

    -- Net Change
    net_change_in_cash          FLOAT,          -- Net Change in Cash
    cash_end_of_period          FLOAT,          -- Cash End of Period
    free_cash_flow              FLOAT,          -- FCF = CFO - CapEx (computed)

    -- Metadata
    created_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (cik, period_date, fiscal_year, fiscal_period)
);