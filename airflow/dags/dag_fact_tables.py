"""
dag_fact_tables.py
------------------
Airflow DAG for loading SEC data into Denormalized Fact Tables.

Schedule: Quarterly, runs after raw staging completes
Pipeline:
    1. Validate S3 files exist
    2. Load into Snowflake FACT_TABLES
    3. Run post-load validation checks
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models.param import Param

import sys
import os
sys.path.append(os.path.dirname(__file__))

from dag_utils import validate_dataset, get_s3_client

default_args = {
    "owner": "janhavi",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="sec_fact_tables_pipeline",
    description="Load SEC data into Snowflake Denormalized Fact Tables",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="0 10 1 1,4,7,10 *",  # 4 hours after raw staging
    catchup=False,
    tags=["sec", "facts", "snowflake"],
    params={
        "dataset": Param("2024q4", type="string", description="Dataset to process e.g. 2024q4"),
    }
) as dag:

    def validate(**context):
        dataset = context["params"]["dataset"]
        ok = validate_dataset(dataset)
        if not ok:
            raise ValueError(f"Validation failed for {dataset}")

    def load_facts(**context):
        dataset = context["params"]["dataset"]
        sys.path.append(os.path.join(os.path.dirname(__file__), "../../snowflake/upload"))
        from load_data import load_fact_tables
        load_fact_tables(dataset)

    def post_load_validation(**context):
        """
        Validate row counts in Snowflake after loading.
        Raises error if any table is empty.
        """
        import snowflake.connector
        from dotenv import load_dotenv
        load_dotenv()

        conn = snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            role=os.getenv("SNOWFLAKE_ROLE"),
        )
        cursor = conn.cursor()

        tables = [
            "FACT_TABLES.BALANCE_SHEET_FACT",
            "FACT_TABLES.INCOME_STATEMENT_FACT",
            "FACT_TABLES.CASH_FLOW_FACT",
        ]

        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM SEC_FINANCIAL.{table}")
            count = cursor.fetchone()[0]
            print(f"{table}: {count:,} rows")
            if count == 0:
                raise ValueError(f"{table} is empty after loading!")

        cursor.close()
        conn.close()
        print("Post-load validation passed!")

    t1 = PythonOperator(
        task_id="validate_s3_files",
        python_callable=validate,
    )

    t2 = PythonOperator(
        task_id="load_fact_tables_to_snowflake",
        python_callable=load_facts,
    )

    t3 = PythonOperator(
        task_id="post_load_validation",
        python_callable=post_load_validation,
    )

    t1 >> t2 >> t3