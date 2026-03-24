-- Staging model for SEC numeric data
-- Cleans and casts RAW_NUM into proper types

{{ config(schema='DBT_STAGING') }}

SELECT
    adsh                                        AS filing_id,
    TRIM(tag)                                   AS xbrl_tag,
    TRIM(version)                               AS tag_version,
    TRY_CAST(ddate AS INTEGER)                  AS data_date,
    TRIM(uom)                                   AS unit_of_measure,
    TRY_CAST(value AS FLOAT)                    AS numeric_value,
    TRY_CAST(qtrs AS INTEGER)                   AS quarters,
    TRIM(coreg)                                 AS co_registrant,
    CURRENT_TIMESTAMP()                         AS dbt_loaded_at

FROM {{ source('raw_staging', 'raw_num') }}

WHERE adsh IS NOT NULL
  AND tag IS NOT NULL
  AND value IS NOT NULL
  AND TRY_CAST(value AS FLOAT) IS NOT NULL