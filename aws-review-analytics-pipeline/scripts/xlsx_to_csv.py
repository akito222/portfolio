"""Excel で受け取ったレビューデータを、S3 に置く前提の CSV に変換する。

- 空行（review_id が欠損）を除外
- ID / 数値列を整数型に戻す（Excel 経由で float 化しているため）
- review_date を YYYY-MM-DD に統一（Glue Crawler が date として推論できる形）
- UTF-8 / LF / ヘッダーあり

Usage:
    python scripts/xlsx_to_csv.py input.xlsx output.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

INT_COLUMNS = [
    "customer_id",
    "age",
    "product_parent",
    "star_rating",
    "helpful_votes",
    "total_votes",
]

COLUMN_ORDER = [
    "marketplace",
    "customer_id",
    "gender",
    "age",
    "review_id",
    "product_id",
    "product_parent",
    "product_title",
    "product_category",
    "star_rating",
    "helpful_votes",
    "total_votes",
    "vine",
    "verified_purchase",
    "review_headline",
    "review_body",
    "review_date",
]


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["review_id"]).copy()
    for col in INT_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    for col in ["review_headline", "review_body", "product_title"]:
        df[col] = df[col].fillna("").astype(str)
    return df[COLUMN_ORDER]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    df = clean(pd.read_excel(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False, encoding="utf-8", lineterminator="\n")
    print(f"wrote {len(df):,} rows -> {args.output}")


if __name__ == "__main__":
    main()
