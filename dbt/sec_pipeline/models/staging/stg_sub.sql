-- Staging model for SEC submission data
-- Cleans and casts RAW_SUB into proper types

{{ config(schema='DBT_STAGING') }}

SELECT
    adsh                                        AS filing_id,
    TRY_CAST(cik AS INTEGER)                    AS cik,
    TRIM(name)                                  AS company_name,
    TRY_CAST(sic AS INTEGER)                    AS sic_code,
    UPPER(TRIM(countryba))                      AS country,
    UPPER(TRIM(stprba))                         AS state,
    TRIM(cityba)                                AS city,
    TRIM(form)                                  AS form_type,
    TRY_CAST(period AS INTEGER)                 AS period_date,
    TRIM(fy)                                    AS fiscal_year,
    TRIM(fp)                                    AS fiscal_period,
    TRY_CAST(filed AS INTEGER)                  AS filed_date,
    CASE WHEN wksi = '1' THEN TRUE ELSE FALSE END AS is_well_known_seasoned_issuer,
    CURRENT_TIMESTAMP()                         AS dbt_loaded_at

FROM {{ source('raw_staging', 'raw_sub') }}

WHERE adsh IS NOT NULL
  AND cik IS NOT NULL
  AND form IS NOT NULL