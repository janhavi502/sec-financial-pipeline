"""
dag_utils.py
------------
Shared utility functions used across all SEC pipeline DAGs.
"""

import os
import io
import boto3
import requests
import zipfile
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME       = os.getenv("AWS_BUCKET_NAME")
AWS_REGION            = os.getenv("AWS_REGION")

SEC_HEADERS = {"User-Agent": "Janhavi Patil patil.janhavi@northeastern.edu"}
SEC_BASE_URL = "https://www.sec.gov/files/dera/data/financial-statement-data-sets"


def get_s3_client():
    """Return a boto3 S3 client."""
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )


def download_sec_dataset(dataset: str) -> bool:
    """
    Download a SEC dataset zip file and upload all TSV files to S3.
    dataset: e.g. '2024q4'
    Returns True if successful.
    """
    url = f"{SEC_BASE_URL}/{dataset}.zip"
    print(f"Downloading {dataset} from {url}...")

    response = requests.get(url, headers=SEC_HEADERS, timeout=120)
    response.raise_for_status()

    s3 = get_s3_client()
    uploaded = []

    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        for filename in z.namelist():
            content = z.read(filename)
            key = f"sec-data/{dataset}/{filename}"
            s3.put_object(
                Bucket=AWS_BUCKET_NAME,
                Key=key,
                Body=content,
                Metadata={"dataset": dataset, "source": "sec.gov"}
            )
            uploaded.append(key)
            print(f"  Uploaded {key}")

    print(f"Done — {len(uploaded)} files uploaded to S3")
    return True


def check_s3_dataset_exists(dataset: str) -> bool:
    """Check if a dataset already exists in S3."""
    s3 = get_s3_client()
    response = s3.list_objects_v2(
        Bucket=AWS_BUCKET_NAME,
        Prefix=f"sec-data/{dataset}/"
    )
    return response.get("KeyCount", 0) > 0


def validate_dataset(dataset: str) -> bool:
    """
    Validate that all 4 required files exist in S3 for a dataset.
    """
    required_files = ["sub.txt", "tag.txt", "num.txt", "pre.txt"]
    s3 = get_s3_client()

    for f in required_files:
        key = f"sec-data/{dataset}/{f}"
        try:
            s3.head_object(Bucket=AWS_BUCKET_NAME, Key=key)
        except Exception:
            print(f"Missing file: {key}")
            return False

    print(f"All 4 files validated for {dataset}")
    return True