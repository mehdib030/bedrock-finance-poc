#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?}"
: "${WORKGROUP_NAME:?}"
: "${DATABASE_NAME:?}"
: "${SQL_FILE:?}"

sql=$(cat "$SQL_FILE")

statement_id=$(aws redshift-data execute-statement \
  --region "$AWS_REGION" \
  --workgroup-name "$WORKGROUP_NAME" \
  --database "$DATABASE_NAME" \
  --sql "$sql" \
  --query Id \
  --output text)

echo "Submitted Redshift bootstrap statement: $statement_id"

while true; do
  status=$(aws redshift-data describe-statement \
    --region "$AWS_REGION" \
    --id "$statement_id" \
    --query Status \
    --output text)

  case "$status" in
    FINISHED)
      echo "Redshift schema bootstrap completed."
      break
      ;;
    FAILED|ABORTED)
      aws redshift-data describe-statement --region "$AWS_REGION" --id "$statement_id"
      exit 1
      ;;
    *) sleep 2 ;;
  esac
done
