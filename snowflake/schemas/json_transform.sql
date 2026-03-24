-- =============================================================
-- JSON TRANSFORMATION SCHEMA
-- Stores each SEC filing as a single JSON object in a VARIANT
-- column. Good for flexible querying without rigid schema.
-- =============================================================

USE DATABASE SEC_FINANCIAL;
USE SCHEMA JSON_TRANSFORM;

-- -------------------------------------------------------------
-- 1. FILING_JSON
--    One row per filing. The entire filing (sub + all its nums)
--    is stored as a nested JSON object in the `payload` column.
-- -------------------------------------------------------------
CREATE OR REPLACE TABLE FILING_JSON (
    adsh            VARCHAR(20)     NOT NULL,   -- Accession number (primary key)
    cik             NUMBER(10),                 -- CIK for easy filtering without parsing JSON
    form            VARCHAR(10),                -- Form type (10-K, 10-Q) for easy filtering
    period          NUMBER(8),                  -- Period end date for easy filtering
    filed           NUMBER(8),                  -- Filed date for easy filtering
    payload         VARIANT         NOT NULL,   -- Full filing JSON object (see structure below)
    created_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (adsh)
);

-- What the payload VARIANT looks like (for reference — not enforced by Snowflake):
-- {
--   "adsh": "0001234567-24-000001",
--   "cik": 12345,
--   "name": "Apple Inc.",
--   "form": "10-K",
--   "period": 20240930,
--   "filed": 20241101,
--   "fy": "2024",
--   "fp": "FY",
--   "sic": 3674,
--   "facts": [
--     {
--       "tag": "Assets",
--       "version": "us-gaap/2023",
--       "ddate": 20240930,
--       "uom": "USD",
--       "value": 364980000000,
--       "stmt": "BS"
--     },
--     ...
--   ]
-- }

-- -------------------------------------------------------------
-- 2. TAG_JSON
--    Tag definitions stored as JSON — same as raw but as VARIANT
--    Useful when you want to join tag metadata dynamically
-- -------------------------------------------------------------
CREATE OR REPLACE TABLE TAG_JSON (
    tag         VARCHAR(256)    NOT NULL,
    version     VARCHAR(20)     NOT NULL,
    payload     VARIANT         NOT NULL,   -- Full tag definition as JSON
    PRIMARY KEY (tag, version)
);

-- =============================================================
-- USEFUL JSON QUERY EXAMPLES (run these after loading data)
-- These show how to query VARIANT columns using Snowflake syntax
-- =============================================================

-- Get company name and total assets from JSON payload
-- SELECT
--     adsh,
--     payload:name::STRING AS company_name,
--     payload:form::STRING AS form_type,
--     f.value:tag::STRING AS tag,
--     f.value:value::FLOAT AS amount
-- FROM FILING_JSON,
-- LATERAL FLATTEN(input => payload:facts) f
-- WHERE f.value:tag::STRING = 'Assets'
-- AND form = '10-K'
-- LIMIT 100;

-- Get all balance sheet items for a specific company
-- SELECT
--     payload:name::STRING AS company,
--     f.value:tag::STRING AS tag,
--     f.value:value::FLOAT AS value,
--     f.value:uom::STRING AS unit
-- FROM FILING_JSON,
-- LATERAL FLATTEN(input => payload:facts) f
-- WHERE cik = 320193  -- Apple
-- AND f.value:stmt::STRING = 'BS';