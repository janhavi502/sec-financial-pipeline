import requests
from bs4 import BeautifulSoup
import boto3
import os
import zipfile
import io
from dotenv import load_dotenv

load_dotenv()

SEC_URL = "https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets"
BASE_DOWNLOAD_URL = "https://www.sec.gov/files/dera/data/financial-statement-data-sets"
HEADERS = {"User-Agent": "Janhavi Patil patil.janhavi@northeastern.edu"}

AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME       = os.getenv("AWS_BUCKET_NAME")
AWS_REGION            = os.getenv("AWS_REGION")


def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )


def scrape_sec_links() -> list[dict]:
    """
    Scrape all dataset download links from the SEC financial statements page.
    Returns a list of dicts with year, quarter, and download URL.
    """
    response = requests.get(SEC_URL, headers=HEADERS, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith(".zip"):
            full_url = f"https://www.sec.gov{href}" if href.startswith("/") else href
            filename = href.split("/")[-1]
            name = filename.replace(".zip", "")
            links.append({
                "filename": filename,
                "name": name,
                "url": full_url
            })

    # If scraping finds no links, fall back to known direct URLs
    if not links:
        print("No links found via scraping, using known direct URLs...")
        known_quarters = [
            "2024q4", "2024q3", "2024q2", "2024q1",
            "2023q4", "2023q3", "2023q2", "2023q1"
        ]
        for q in known_quarters:
            links.append({
                "filename": f"{q}.zip",
                "name": q,
                "url": f"{BASE_DOWNLOAD_URL}/{q}.zip"
            })

    print(f"Found {len(links)} datasets")
    for l in links[:5]:
        print(f"  {l['name']} → {l['url']}")

    return links


def download_and_upload_dataset(dataset: dict) -> dict:
    """
    Download a specific SEC dataset zip file, extract it,
    and upload all TSV files to S3.
    """
    s3 = get_s3_client()
    name = dataset["name"]  # e.g. 2024q4
    url  = dataset["url"]

    print(f"\nDownloading {name}...")
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()

    uploaded_files = []

    # Extract zip in memory
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        for filename in z.namelist():
            print(f"  Uploading {filename}...")
            content = z.read(filename)
            s3_key = f"sec-data/{name}/{filename}"

            s3.put_object(
                Bucket=AWS_BUCKET_NAME,
                Key=s3_key,
                Body=content,
                Metadata={"dataset": name, "source": "sec.gov"}
            )
            uploaded_files.append(s3_key)

    print(f"Uploaded {len(uploaded_files)} files for {name}")
    return {"dataset": name, "files": uploaded_files}


def list_s3_datasets(prefix: str = "sec-data/") -> list:
    """List all SEC datasets currently in S3."""
    s3 = get_s3_client()
    response = s3.list_objects_v2(Bucket=AWS_BUCKET_NAME, Prefix=prefix)
    files = [obj["Key"] for obj in response.get("Contents", [])]
    return files


if __name__ == "__main__":
    # Step 1: Scrape all links
    links = scrape_sec_links()

    # Step 2: Download and upload Q4 2024 dataset to S3
    target = next((l for l in links if "2024q4" in l["name"].lower()), None)

    if target:
        result = download_and_upload_dataset(target)
        print(f"\nDone! Files in S3:")
        for f in result["files"]:
            print(f"  {f}")
    else:
        print("Q4 2024 dataset not found — available datasets:")
        for l in links:
            print(f"  {l['name']}")