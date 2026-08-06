# Day 2 — SEC ingestion and demo normalization

Run from the project root after Day 1 Terraform deployment.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1
export SEC_USER_AGENT="Your Name your.email@example.com"
export BUCKET=$(terraform -chdir=../sec-bedrock-text-to-sql-terraform-day1 output -raw data_bucket_name)

python ingestion/download_extract_upload.py --bucket "$BUCKET" --work-dir work
python ingestion/normalize_demo_data.py --bucket "$BUCKET" --work-dir work --output-dir output
```

The scripts preserve the eight 2024–2025 ZIP files plus 2026 Q1, upload `sub.txt`, `num.txt`, and `tag.txt`, and create a reduced Parquet/CSV semantic dataset for Apple, Microsoft, Amazon, Alphabet, and Meta.
