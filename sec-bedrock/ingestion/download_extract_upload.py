from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import boto3
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

QUARTERS = [
    "2024q1", "2024q2", "2024q3", "2024q4",
    "2025q1", "2025q2", "2025q3", "2025q4", "2026q1",
]
EXPECTED = {"sub.txt", "num.txt", "tag.txt", "pre.txt"}
KEEP = {"sub.txt", "num.txt", "tag.txt"}


def session(user_agent: str) -> requests.Session:
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        status=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"})
    return s


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def upload(s3, path: Path, bucket: str, key: str, content_type: str, metadata: dict[str, str]) -> None:
    s3.upload_file(
        str(path), bucket, key,
        ExtraArgs={"ContentType": content_type, "Metadata": metadata},
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--work-dir", default="work")
    parser.add_argument("--user-agent", default=os.getenv("SEC_USER_AGENT"))
    parser.add_argument("--skip-existing", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    if not args.user_agent:
        raise SystemExit("Set SEC_USER_AGENT or pass --user-agent 'Name email@example.com'")

    work = Path(args.work_dir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    http = session(args.user_agent)
    s3 = boto3.client("s3")
    manifest: list[dict] = []

    s3.head_bucket(Bucket=args.bucket)

    for quarter in QUARTERS:
        year, q = quarter[:4], quarter[-1]
        qdir = work / quarter
        qdir.mkdir(parents=True, exist_ok=True)
        zip_path = qdir / f"{quarter}.zip"
        zip_key = f"raw/sec/zips/{quarter}.zip"
        url = f"https://www.sec.gov/files/dera/data/financial-statement-data-sets/{quarter}.zip"

        exists = False
        if args.skip_existing:
            try:
                s3.head_object(Bucket=args.bucket, Key=zip_key)
                exists = True
            except s3.exceptions.ClientError as exc:
                if str(exc.response.get("Error", {}).get("Code")) not in {"404", "NoSuchKey", "NotFound"}:
                    raise

        if not zip_path.exists():
            print(f"Downloading {url}")
            with http.get(url, stream=True, timeout=(30, 300)) as response:
                response.raise_for_status()
                with zip_path.open("wb") as out:
                    for chunk in response.iter_content(1024 * 1024):
                        if chunk:
                            out.write(chunk)

        if not zipfile.is_zipfile(zip_path):
            raise RuntimeError(f"Invalid ZIP: {zip_path}")

        with zipfile.ZipFile(zip_path) as archive:
            members = {
                Path(info.filename).name.lower(): info
                for info in archive.infolist() if not info.is_dir()
            }
            missing = EXPECTED - set(members)
            if missing:
                raise RuntimeError(f"{quarter} missing {sorted(missing)}")
            corrupt = archive.testzip()
            if corrupt:
                raise RuntimeError(f"{quarter} corrupt member: {corrupt}")

            extracted = {}
            for filename in KEEP:
                target = qdir / filename
                with archive.open(members[filename]) as src, target.open("wb") as dst:
                    while chunk := src.read(1024 * 1024):
                        dst.write(chunk)
                extracted[filename] = target.stat().st_size

        digest = sha256(zip_path)
        metadata = {"source": "sec-financial-statement-data-set", "quarter": quarter, "sha256": digest}
        if not exists:
            print(f"Uploading s3://{args.bucket}/{zip_key}")
            upload(s3, zip_path, args.bucket, zip_key, "application/zip", metadata)

        for filename in KEEP:
            table = filename.removesuffix(".txt")
            key = f"raw/sec/{table}/year={year}/quarter=Q{q}/{filename}"
            print(f"Uploading s3://{args.bucket}/{key}")
            upload(s3, qdir / filename, args.bucket, key, "text/tab-separated-values", metadata)

        record = {
            "quarter": quarter,
            "source_url": url,
            "zip_s3_key": zip_key,
            "zip_size_bytes": zip_path.stat().st_size,
            "sha256": digest,
            "zip_valid": True,
            "sub_size_bytes": extracted["sub.txt"],
            "num_size_bytes": extracted["num.txt"],
            "tag_size_bytes": extracted["tag.txt"],
            "loaded_at": datetime.now(timezone.utc).isoformat(),
        }
        manifest.append(record)
        manifest_path = work / "ingestion_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        s3.upload_file(str(manifest_path), args.bucket, "raw/sec/manifests/ingestion_manifest.json")
        time.sleep(0.25)

    print(json.dumps({"quarters": len(manifest), "manifest": str(work / 'ingestion_manifest.json')}, indent=2))


if __name__ == "__main__":
    main()
