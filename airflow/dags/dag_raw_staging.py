"""
dag_raw_staging.py
------------------
Airflow DAG for downloading SEC data and loading into Raw Staging tables.

Schedule: Quarterly (runs automatically after each quarter ends)
Pipeline:
    1. Check if dataset exists in S3
    2. Download from SEC if not already there
    3. Validate all 4 files exist
    4. Load into Snowflake RAW_STAGING tables
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models.param import Param

import sys
import os
sys.path.append(os.path.dirname(__file__))

from dag_utils import download_sec_dataset, check_s3_dataset_exists, validate_dataset

# ── Default args ───────────────────────────────────────────────
default_args = {
    "owner": "janhavi",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

# ── DAG definition ─────────────────────────────────────────────
with DAG(
    dag_id="sec_raw_staging_pipeline",
    description="Download SEC data and load into Snowflake Raw Staging",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="0 6 1 1,4,7,10 *",  # 6am on Jan 1, Apr 1, Jul 1, Oct 1
    catchup=False,
    tags=["sec", "raw", "snowflake"],
    params={
        "dataset": Param("2024q4", type="string", description="Dataset to process e.g. 2024q4"),
    }
) as dag:

    def check_or_download(**context):
        dataset = context["params"]["dataset"]
        if check_s3_dataset_exists(dataset):
            print(f"{dataset} already in S3 — skipping download")
        else:
            download_sec_dataset(dataset)

    def validate(**context):
        dataset = context["params"]["dataset"]
        ok = validate_dataset(dataset)
        if not ok:
            raise ValueError(f"Validation failed for {dataset} — missing files in S3")
        print(f"Validation passed for {dataset}")

    def load_raw(**context):
        dataset = context["params"]["dataset"]
        # Import here to avoid Airflow import issues
        sys.path.append(os.path.join(os.path.dirname(__file__), "../../snowflake/upload"))
        from load_data import load_raw_staging
        load_raw_staging(dataset)

    # ── Tasks ──────────────────────────────────────────────────
    t1 = PythonOperator(
        task_id="check_or_download_from_sec",
        python_callable=check_or_download,
    )

    t2 = PythonOperator(
        task_id="validate_s3_files",
        python_callable=validate,
    )

    t3 = PythonOperator(
        task_id="load_raw_staging_to_snowflake",
        python_callable=load_raw,
    )

    # ── Task order ─────────────────────────────────────────────
    t1 >> t2 >> t3