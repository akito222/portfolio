"""Run a .sql file on Athena and print the result and the bytes scanned.

    python scripts/athena_query.py sql/handson/h3_books_high_rating_csv.sql
    python scripts/athena_query.py sql/handson/h3_books_high_rating_parquet.sql

The workgroup enforces the result location, so no OutputLocation is passed here.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import boto3


def run_query(client, sql: str, workgroup: str, database: str) -> dict:
    qid = client.start_query_execution(
        QueryString=sql,
        WorkGroup=workgroup,
        QueryExecutionContext={"Database": database},
    )["QueryExecutionId"]
    while True:
        q = client.get_query_execution(QueryExecutionId=qid)["QueryExecution"]
        state = q["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(1)
    if state != "SUCCEEDED":
        raise RuntimeError(f"{state}: {q['Status'].get('StateChangeReason')}")
    return q


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("sql_file", type=Path)
    p.add_argument("--workgroup", default="review-analytics-wg")
    p.add_argument("--database", default="review_analytics")
    p.add_argument("--max-rows", type=int, default=20)
    args = p.parse_args()

    client = boto3.client("athena")
    sql = args.sql_file.read_text(encoding="utf-8").strip().rstrip(";")
    q = run_query(client, sql, args.workgroup, args.database)

    rows = client.get_query_results(QueryExecutionId=q["QueryExecutionId"], MaxResults=args.max_rows + 1)
    for row in rows["ResultSet"]["Rows"]:
        print(" | ".join(c.get("VarCharValue", "") for c in row["Data"]))

    stats = q["Statistics"]
    print(
        f"\n-- scanned {stats['DataScannedInBytes'] / 1024 / 1024:,.2f} MiB, "
        f"engine {stats['EngineExecutionTimeInMillis']} ms"
    )


if __name__ == "__main__":
    main()
