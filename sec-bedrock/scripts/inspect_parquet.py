# scripts/inspect_parquet.py

from pathlib import Path

import pyarrow.parquet as pq


def main() -> None:
    parquet_files = list(
        Path("./output/company_financial_metrics").glob("*.parquet")
    )

    if not parquet_files:
        raise FileNotFoundError("No Parquet files were found.")

    parquet_file = parquet_files[0]
    table = pq.read_table(parquet_file)

    print(f"File: {parquet_file}")
    print(f"Rows: {table.num_rows}")
    print("\nSchema:")
    print(table.schema)

    print("\nFirst five rows:")
    print(table.slice(0, 5).to_pandas().to_string(index=False))


if __name__ == "__main__":
    main()