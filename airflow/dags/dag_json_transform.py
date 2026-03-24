"""
dag_json_transform.py
---------------------
Airflow DAG for loading SEC data into JSON Transform tables.

Schedule: Quarterly, runs after raw staging completes
Pipeline:
    1. Validate S3 files exist
    2. Load into Snowflake JSON_TRANSFORM tables
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models.param import Param

import sys
import os
sys.path.append(os.path.dirname(__file__))

from dag_utils import validate_dataset

default_args = {
    "owner": "janhavi",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="sec_json_transform_pipeline",
    description="Load SEC data into Snowflake JSON Transform tables",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="0 8 1 1,4,7,10 *",  # 2 hours after raw staging
    catchup=False,
    tags=["sec", "json", "snowflake"],
    params={
        "dataset": Param("2024q4", type="string", description="Dataset to process e.g. 2024q4"),
    }
) as dag:

    def validate(**context):
        dataset = context["params"]["dataset"]
        ok = validate_dataset(dataset)
        if not ok:
            raise ValueError(f"Validation failed for {dataset}")

    def load_json(**context):
        dataset = context["params"]["dataset"]
        sys.path.append(os.path.join(os.path.dirname(__file__), "../../snowflake/upload"))
        from load_data import load_json_transform
        load_json_transform(dataset)

    t1 = PythonOperator(
        task_id="validate_s3_files",
        python_callable=validate,
    )

    t2 = PythonOperator(
        task_id="load_json_transform_to_snowflake",
        python_callable=load_json,
    )

    t1 >> t2