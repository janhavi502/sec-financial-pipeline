-- =============================================================
-- RAW STAGING SCHEMA
-- Stores SEC data exactly as-is from the TSV files.
-- No transformation — pure 1:1 mirror of the source files.
-- =============================================================

USE DATABASE SEC_FINANCIAL;
USE SCHEMA RAW_STAGING;

-- -------------------------------------------------------------
-- 1. SUB (Submissions) — one row per filing
--    Describes the company and the filing itself
-- -------------------------------------------------------------
CREATE OR REPLACE TABLE RAW_SUB (
    adsh        VARCHAR(20)     NOT NULL,   -- Accession number (unique filing ID)
    cik         NUMBER(10)      NOT NULL,   -- SEC company identifier
    name        VARCHAR(150),               -- Company name
    sic         NUMBER(4),                  -- Standard Industry Code
    countryba   VARCHAR(2),                 -- Country of business address
    stprba      VARCHAR(2),                 -- State/province of business address
    cityba      VARCHAR(30),                -- City of business address
    zipba       VARCHAR(10),                -- Zip of business address
    bas1        VARCHAR(40),                -- Business address street line 1
    bas2        VARCHAR(40),                -- Business address street line 2
    baph        VARCHAR(20),                -- Business phone
    countryma   VARCHAR(2),                 -- Country of mailing address
    stprma      VARCHAR(2),                 -- State/province of mailing address
    cityma      VARCHAR(30),                -- City of mailing address
    zipma       VARCHAR(10),                -- Zip of mailing address
    mas1        VARCHAR(40),                -- Mailing address street line 1
    mas2        VARCHAR(40),                -- Mailing address street line 2
    countryinc  VARCHAR(2),                 -- Country of incorporation
    stprinc     VARCHAR(2),                 -- State of incorporation
    ein         NUMBER(10),                 -- Employer Identification Number
    former      VARCHAR(150),               -- Former company name
    changed     VARCHAR(8),                 -- Date of name change
    afs         VARCHAR(5),                 -- Filer status (Large Accelerated, etc.)
    wksi        NUMBER(1),                  -- Well-known seasoned issuer flag
    fye         VARCHAR(4),                 -- Fiscal year end (MMDD)
    form        VARCHAR(10),                -- Submission type (10-K, 10-Q, etc.)
    period      NUMBER(8),                  -- Balance sheet date (YYYYMMDD)
    fy          VARCHAR(4),                 -- Fiscal year
    fp          VARCHAR(2),                 -- Fiscal period (Q1, Q2, Q3, FY)
    filed       NUMBER(8),                  -- Filed date (YYYYMMDD)
    accepted    TIMESTAMP_NTZ,              -- Accepted datetime
    prevrpt     NUMBER(1),                  -- Previous report flag
    detail      NUMBER(1),                  -- Detail flag
    instance    VARCHAR(40),                -- Instance document filename
    nciks       NUMBER(4),                  -- Number of CIKs in filing
    aciks       VARCHAR(120)                -- Additional CIKs
);

-- -------------------------------------------------------------
-- 2. TAG — financial concept definitions (XBRL taxonomy)
--    Describes what each financial tag means
-- -------------------------------------------------------------
CREATE OR REPLACE TABLE RAW_TAG (
    tag         VARCHAR(256)    NOT NULL,   -- XBRL tag name (e.g. Assets, Revenue)
    version     VARCHAR(20)     NOT NULL,   -- Taxonomy version (e.g. us-gaap/2023)
    custom      NUMBER(1),                  -- 1 = company-defined, 0 = standard
    abstract    NUMBER(1),                  -- 1 = abstract (grouping only, no value)
    datatype    VARCHAR(20),                -- Data type (monetaryItemType, etc.)
    iord        VARCHAR(1),                 -- Instant or Duration (I/D)
    crdr        VARCHAR(1),                 -- Credit or Debit (C/D)
    tlabel      VARCHAR(512),               -- Human-readable label
    doc         VARCHAR(2048)               -- Documentation / description
);

-- -------------------------------------------------------------
-- 3. NUM — the actual numeric financial values
--    One row per data point per filing
-- -------------------------------------------------------------
CREATE OR REPLACE TABLE RAW_NUM (
    adsh        VARCHAR(20)     NOT NULL,   -- Accession number (links to SUB)
    tag         VARCHAR(256)    NOT NULL,   -- XBRL tag (links to TAG)
    version     VARCHAR(20)     NOT NULL,   -- Taxonomy version (links to TAG)
    ddate       NUMBER(8)       NOT NULL,   -- Data date (YYYYMMDD)
    uom         VARCHAR(20)     NOT NULL,   -- Unit of measure (USD, shares, etc.)
    coreg       VARCHAR(256),               -- Co-registrant (blank = parent entity)
    value       FLOAT,                      -- The actual numeric value
    footnote    VARCHAR(512)                -- Footnote text if any
);

-- -------------------------------------------------------------
-- 4. PRE — presentation linkbase (report structure)
--    Defines how tags are organized in financial statements
-- -------------------------------------------------------------
CREATE OR REPLACE TABLE RAW_PRE (
    adsh        VARCHAR(20)     NOT NULL,   -- Accession number (links to SUB)
    report      NUMBER(6)       NOT NULL,   -- Report number within filing
    line        NUMBER(6)       NOT NULL,   -- Line number within report
    stmt        VARCHAR(2),                 -- Statement type (BS, IS, CF, EQ, CI, UN, CP)
    inpth       NUMBER(1),                  -- In-path flag (1 = detail row)
    rfile       VARCHAR(1),                 -- Report file type (R = rendered)
    tag         VARCHAR(256),               -- XBRL tag
    version     VARCHAR(20),                -- Taxonomy version
    prole       VARCHAR(256),               -- Preferred role
    plabel      VARCHAR(512),               -- Preferred label
    negating    NUMBER(1)                   -- Negating flag
);