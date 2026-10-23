"""Reproduce the AWS pipeline locally with DuckDB + pandas and record the results.

AWS service            -> local stand-in
--------------------------------------------------------------
S3 raw/ CSV            -> data/amazon_reviews_5.csv (external view, scanned on every query)
Glue Data Catalog      -> DuckDB schema `review_analytics`
Athena (Trino SQL)     -> DuckDB SQL; the very same files in sql/ are executed
DataBrew recipe job    -> local/databrew_local.py applying databrew/recipe.json
Glue ETL (Parquet)     -> DuckDB COPY ... (FORMAT parquet, COMPRESSION snappy, PARTITION_BY)
Amazon Quick           -> matplotlib charts in docs/images/
Bedrock output         -> optional: data/ai_reviews_output.jsonl (your real output, if any)

    python local/run_local.py                 # full data
    python local/run_local.py --data-dir tests/fixtures --out /tmp/out   # tiny smoke test
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from databrew_local import apply_recipe, load_recipe  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DB = "review_analytics"

CSV_COLUMNS = {
    "marketplace": "VARCHAR",
    "customer_id": "BIGINT",
    "gender": "VARCHAR",
    "age": "INTEGER",
    "review_id": "VARCHAR",
    "product_id": "VARCHAR",
    "product_parent": "BIGINT",
    "product_title": "VARCHAR",
    "product_category": "VARCHAR",
    "star_rating": "INTEGER",
    "helpful_votes": "INTEGER",
    "total_votes": "INTEGER",
    "vine": "VARCHAR",
    "verified_purchase": "VARCHAR",
    "review_headline": "VARCHAR",
    "review_body": "VARCHAR",
    "review_date": "DATE",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def sql_file(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip().rstrip(";")


def csv_source(path: Path) -> str:
    cols = ", ".join(f"'{k}': '{v}'" for k, v in CSV_COLUMNS.items())
    return f"read_csv('{path.as_posix()}', header=true, quote='\"', columns={{{cols}}})"


def md_table(df: pd.DataFrame, max_rows: int = 10) -> str:
    out = df.head(max_rows).copy()
    for c in out.select_dtypes("float").columns:
        out[c] = out[c].round(3)
    return out.to_markdown(index=False)


def human(n: float) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:,.1f} {unit}"
        n /= 1024
    return f"{n:,.1f} TB"


def parquet_bytes(files: list[Path], columns: set[str] | None = None) -> int:
    """Compressed bytes of the given column chunks (= what a columnar engine reads)."""
    total = 0
    for f in files:
        meta = pq.ParquetFile(f).metadata
        for rg in range(meta.num_row_groups):
            g = meta.row_group(rg)
            for ci in range(g.num_columns):
                col = g.column(ci)
                if columns is None or col.path_in_schema in columns:
                    total += col.total_compressed_size
    return total


# ---------------------------------------------------------------------------
# steps
# ---------------------------------------------------------------------------
class Report:
    def __init__(self) -> None:
        self.parts: list[str] = []

    def h(self, text: str, level: int = 2) -> None:
        self.parts.append(f"\n{'#' * level} {text}\n")

    def p(self, text: str) -> None:
        self.parts.append(text)

    def query(self, title: str, path: Path, df: pd.DataFrame, secs: float, max_rows: int = 10) -> None:
        rel = path.relative_to(ROOT).as_posix()
        self.parts.append(
            f"**{title}** — [`{rel}`](../{rel}) · {len(df):,} rows · {secs * 1000:,.0f} ms\n\n"
            f"{md_table(df, max_rows)}\n"
        )

    def write(self, path: Path) -> None:
        path.write_text("\n".join(self.parts), encoding="utf-8")


def run_sql(con, path: Path) -> tuple[pd.DataFrame, float]:
    t = time.perf_counter()
    df = con.execute(sql_file(path)).df()
    return df, time.perf_counter() - t


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=ROOT / "data")
    ap.add_argument("--out", type=Path, default=ROOT / "docs")
    ap.add_argument("--work", type=Path, default=ROOT / "local" / ".work")
    ap.add_argument("--no-charts", action="store_true")
    args = ap.parse_args()

    raw_csv = args.data_dir / "amazon_reviews_5.csv"
    add_csv = args.data_dir / "amazon_reviews_add.csv"
    ai_jsonl = args.data_dir / "ai_reviews_output.jsonl"
    if args.work.exists():
        shutil.rmtree(args.work)
    args.work.mkdir(parents=True)
    (args.out / "images").mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute(f"CREATE SCHEMA {DB}")
    # "crawler": register the CSV as an external table (a view that re-reads the file)
    con.execute(f"CREATE VIEW {DB}.amazon_reviews AS SELECT * FROM {csv_source(raw_csv)}")

    rep = Report()
    rep.p("# ローカル再現の実行結果\n")
    rep.p(
        "> `python local/run_local.py` が自動生成するファイルです。AWS上の Athena / DataBrew / Glue ETL と同じ処理を "
        "DuckDB + pandas で実行し、**`sql/` のSQLファイルをそのまま**流しています。"
    )
    n_rows = con.execute(f"SELECT COUNT(*) FROM {DB}.amazon_reviews").fetchone()[0]
    rep.p(f"\n入力: `{raw_csv.name}` {n_rows:,} 行 / {human(raw_csv.stat().st_size)}\n")
    results: dict[str, pd.DataFrame] = {}

    # ---- Hands-on 1 -------------------------------------------------------
    rep.h("ハンズオン1: Athena でクエリ")
    p = ROOT / "sql/handson/h1_top10_customers.sql"
    df, s = run_sql(con, p)
    results["top10"] = df
    rep.query("レビュー数が多いお客様 Top10", p, df, s)

    # Quick visual equivalents
    results["titles"] = con.execute(
        f"SELECT product_title, COUNT(star_rating) AS reviews FROM {DB}.amazon_reviews "
        "GROUP BY product_title ORDER BY reviews DESC, product_title LIMIT 10"
    ).df()
    results["cat_products"] = con.execute(
        f"SELECT product_category, COUNT(DISTINCT product_id) AS products FROM {DB}.amazon_reviews "
        "GROUP BY product_category ORDER BY products DESC"
    ).df()

    # ---- Hands-on 2: DataBrew recipe on 2 datasets ---------------------------
    rep.h("ハンズオン2 / 追加課題: DataBrew レシピの再利用")
    steps = load_recipe(ROOT / "databrew/recipe.json")
    outputs = {}
    for name, path in [("reviews", raw_csv), ("reviews_add", add_csv)]:
        if not path.exists():
            continue
        src = con.execute(f"SELECT * FROM {csv_source(path)}").df()
        t = time.perf_counter()
        out = apply_recipe(src, steps)
        secs = time.perf_counter() - t
        dest = args.work / "curated" / "databrew" / name
        dest.mkdir(parents=True)
        out.to_parquet(dest / "part-0000.snappy.parquet", compression="snappy", index=False)
        outputs[name] = (src, out, secs)
    rows = []
    for name, (src, out, secs) in outputs.items():
        new_cols = [c for c in out.columns if c not in src.columns]
        rows.append(
            {
                "dataset": name,
                "rows": len(out),
                "input cols": src.shape[1],
                "output cols": out.shape[1],
                "added": ", ".join(new_cols),
                "sec": round(secs, 2),
            }
        )
    rep.p(md_table(pd.DataFrame(rows)))
    if len(outputs) == 2:
        a, b = outputs["reviews"][1], outputs["reviews_add"][1]
        same = list(a.columns) == list(b.columns) and all(a.dtypes == b.dtypes)
        rep.p(f"\n同じ `databrew/recipe.json` を2つのデータセットに適用 → 出力スキーマ一致: **{same}**\n")
        if not same:
            raise SystemExit("recipe reuse produced different schemas")
    sample = outputs["reviews"][1][
        [
            "product_category",
            "star_rating",
            "category_star_rating_mean",
            "product_star_rating_mean",
            "verified_purchase_Yes",
            "verified_purchase_No",
        ]
    ]
    rep.p("\n変換後サンプル:\n\n" + md_table(sample, 5))

    # ---- Hands-on 3: CSV vs partitioned Parquet --------------------------------
    rep.h("ハンズオン3: CSV → Parquet + パーティションでスキャン量を削減")
    pq_dir = args.work / "curated" / "reviews_parquet"
    t = time.perf_counter()
    con.execute(
        f"COPY (SELECT * EXCLUDE (total_votes, vine) FROM {DB}.amazon_reviews) TO '{pq_dir.as_posix()}' "
        "(FORMAT parquet, COMPRESSION snappy, PARTITION_BY (product_category))"
    )
    etl_secs = time.perf_counter() - t
    con.execute(
        f"CREATE VIEW {DB}.reviews_parquet AS SELECT * FROM "
        f"read_parquet('{pq_dir.as_posix()}/**/*.parquet', hive_partitioning=true)"
    )
    p_csv = ROOT / "sql/handson/h3_books_high_rating_csv.sql"
    p_pq = ROOT / "sql/handson/h3_books_high_rating_parquet.sql"
    df_csv, s_csv = run_sql(con, p_csv)
    df_pq, s_pq = run_sql(con, p_pq)
    pd.testing.assert_frame_equal(df_csv.reset_index(drop=True), df_pq.reset_index(drop=True))

    all_files = sorted(pq_dir.rglob("*.parquet"))
    books_files = [f for f in all_files if "product_category=Books" in f.as_posix()]
    csv_bytes = raw_csv.stat().st_size
    pq_total = sum(f.stat().st_size for f in all_files)
    pq_books_all_cols = parquet_bytes(books_files)
    pq_books_needed = parquet_bytes(books_files, {"product_title", "star_rating"})
    scan = pd.DataFrame(
        [
            {"読む対象": "CSV（行指向・パーティションなし）: ファイル全体", "bytes": csv_bytes},
            {"読む対象": "Parquet 全パーティション・全列", "bytes": pq_total},
            {"読む対象": "Parquet Books パーティションのみ・全列", "bytes": pq_books_all_cols},
            {"読む対象": "Parquet Books のみ・必要な2列だけ", "bytes": pq_books_needed},
        ]
    )
    scan["size"] = scan["bytes"].map(human)
    scan["CSV比"] = (scan["bytes"] / csv_bytes).map(lambda r: f"{r:.2%}")
    results["scan"] = scan
    rep.p(
        f"ETL（CSV→Parquet/Snappy, product_category でパーティション）: {etl_secs:.1f} s, "
        f"{len(all_files)} ファイル / {len(list(pq_dir.iterdir()))} パーティション\n"
    )
    rep.p(md_table(scan[["読む対象", "size", "CSV比"]]))
    rep.p(
        f"\n2つのクエリ結果は完全一致（{len(df_csv):,} 行）。ローカル実行時間 CSV {s_csv * 1000:,.0f} ms → Parquet {s_pq * 1000:,.0f} ms。\n"
        "Athena は**スキャンしたバイト数で課金**されるので、最下行がそのままコスト削減率の目安になる。\n"
    )
    rep.query("Books で平均★4.5以上（Parquet版・上位）", p_pq, df_pq, s_pq, 5)

    # ---- Additional tasks: SQL ------------------------------------------------
    rep.h("追加課題: Athena クエリ")
    for name in [
        "a1_step3_female_categories_by_avg_rating",
        "a1_extra_female_categories_reliable",
        "a2_step3_age_by_review_count",
        "a3_step2_information_schema_amazon_reviews",
    ]:
        p = ROOT / f"sql/additional/{name}.sql"
        df, s = run_sql(con, p)
        results[name] = df
        rep.query(name, p, df, s)
    rep.p(
        "※ ローカルでは CSV を VIEW として登録しているため table_type は `VIEW`。"
        "Athena では Glue の外部テーブルとして `BASE TABLE` が返る。\n"
    )
    for name in [
        "a1_step1_female_categories",
        "a1_step2_female_categories_grouped",
        "a2_step1_age",
        "a2_step2_age_grouped",
        "a3_step1_information_schema",
    ]:
        df, s = run_sql(con, ROOT / f"sql/additional/{name}.sql")  # executed to prove they run
        rep.p(f"- `{name}.sql`: {len(df):,} rows ({s * 1000:,.0f} ms)")

    # ---- Hands-on 4 (optional): real Bedrock output -----------------------------
    rep.h("ハンズオン4: Bedrock 出力とのJOIN（ギャップ検知）")
    if ai_jsonl.exists():
        con.execute(f"CREATE VIEW {DB}.ai_reviews_output AS SELECT * FROM read_json_auto('{ai_jsonl.as_posix()}')")
        for name in ["h4_rating_x_sentiment", "h4_gap_detection"]:
            p = ROOT / f"sql/handson/{name}.sql"
            df, s = run_sql(con, p)
            results[name] = df
            rep.query(name, p, df, s, 15)
    else:
        rep.p(
            "`data/ai_reviews_output.jsonl` が無いためスキップ（Bedrock を呼んだ実出力を置くと同じSQLで集計される）。"
        )

    args.out.mkdir(parents=True, exist_ok=True)
    rep.write(args.out / "local-results.md")
    print(f"report -> {args.out / 'local-results.md'}")

    if not args.no_charts:
        from charts import render_all

        render_all(results, args.out / "images")
        print(f"charts -> {args.out / 'images'}")


if __name__ == "__main__":
    main()
