# ローカル再現の実行結果

> `python local/run_local.py` が自動生成するファイルです。AWS上の Athena / DataBrew / Glue ETL と同じ処理を DuckDB + pandas で実行し、**`sql/` のSQLファイルをそのまま**流しています。

入力: `amazon_reviews_5.csv` 170,296 行 / 148.7 MB


## ハンズオン1: Athena でクエリ

**レビュー数が多いお客様 Top10** — [`sql/handson/h1_top10_customers.sql`](../sql/handson/h1_top10_customers.sql) · 10 rows · 348 ms

|   customer_id |   count_review |
|--------------:|---------------:|
|      35106293 |            686 |
|      33605019 |            426 |
|      34982749 |            388 |
|      37296285 |            383 |
|      49031952 |            352 |
|      37487202 |            295 |
|      38184548 |            272 |
|      34277466 |            263 |
|      34250468 |            254 |
|      48706054 |            235 |


## ハンズオン2 / 追加課題: DataBrew レシピの再利用

| dataset     |   rows |   input cols |   output cols | added                                                                                                                 |   sec |
|:------------|-------:|-------------:|--------------:|:----------------------------------------------------------------------------------------------------------------------|------:|
| reviews     | 170296 |           17 |            22 | product_title_lower, category_star_rating_mean, product_star_rating_mean, verified_purchase_No, verified_purchase_Yes |  0.08 |
| reviews_add | 149656 |           17 |            22 | product_title_lower, category_star_rating_mean, product_star_rating_mean, verified_purchase_No, verified_purchase_Yes |  0.14 |

同じ `databrew/recipe.json` を2つのデータセットに適用 → 出力スキーマ一致: **True**


変換後サンプル:

| product_category   |   star_rating |   category_star_rating_mean |   product_star_rating_mean |   verified_purchase_Yes |   verified_purchase_No |
|:-------------------|--------------:|----------------------------:|---------------------------:|------------------------:|-----------------------:|
| Video DVD          |             1 |                       4.059 |                      2.75  |                       0 |                      1 |
| Video DVD          |             3 |                       4.059 |                      4     |                       0 |                      1 |
| Video DVD          |             4 |                       4.059 |                      3.556 |                       0 |                      1 |
| Video DVD          |             5 |                       4.059 |                      5     |                       0 |                      1 |
| Video DVD          |             2 |                       4.059 |                      4.05  |                       0 |                      1 |

## ハンズオン3: CSV → Parquet + パーティションでスキャン量を削減

ETL（CSV→Parquet/Snappy, product_category でパーティション）: 1.8 s, 30 ファイル / 30 パーティション

| 読む対象                       | size     | CSV比    |
|:---------------------------|:---------|:--------|
| CSV（行指向・パーティションなし）: ファイル全体 | 148.7 MB | 100.00% |
| Parquet 全パーティション・全列        | 75.3 MB  | 50.66%  |
| Parquet Books パーティションのみ・全列 | 5.0 MB   | 3.37%   |
| Parquet Books のみ・必要な2列だけ   | 196.4 KB | 0.13%   |

2つのクエリ結果は完全一致（2,218 行）。ローカル実行時間 CSV 225 ms → Parquet 9 ms。
Athena は**スキャンしたバイト数で課金**されるので、最下行がそのままコスト削減率の目安になる。

**Books で平均★4.5以上（Parquet版・上位）** — [`sql/handson/h3_books_high_rating_parquet.sql`](../sql/handson/h3_books_high_rating_parquet.sql) · 2,218 rows · 9 ms

| product_title                                             |   avg_rate |
|:----------------------------------------------------------|-----------:|
| 23 Things They Don't Tell You About Capitalism            |        4.5 |
| A Feast for Crows: A Song of Ice and Fire: Book Four      |        4.5 |
| A Photographer's Life: 1990-2005                          |        4.5 |
| A Whole New Mind: Why Right-Brainers Will Rule the Future |        4.5 |
| Abc3d                                                     |        4.5 |


## 追加課題: Athena クエリ

**a1_step3_female_categories_by_avg_rating** — [`sql/additional/a1_step3_female_categories_by_avg_rating.sql`](../sql/additional/a1_step3_female_categories_by_avg_rating.sql) · 30 rows · 182 ms

| product_category       |   avg_rating |
|:-----------------------|-------------:|
| Lawn and Garden        |        5     |
| Digital_Ebook_Purchase |        4.539 |
| Video                  |        4.503 |
| Books                  |        4.484 |
| Music                  |        4.458 |
| Digital_Music_Purchase |        4.429 |
| Baby                   |        4.412 |
| Toys                   |        4.404 |
| Watches                |        4.213 |
| Shoes                  |        4.187 |

**a1_extra_female_categories_reliable** — [`sql/additional/a1_extra_female_categories_reliable.sql`](../sql/additional/a1_extra_female_categories_reliable.sql) · 22 rows · 190 ms

| product_category       |   avg_rating |   review_count |
|:-----------------------|-------------:|---------------:|
| Digital_Ebook_Purchase |        4.539 |            686 |
| Video                  |        4.503 |            366 |
| Books                  |        4.484 |           4413 |
| Music                  |        4.458 |          25319 |
| Digital_Music_Purchase |        4.429 |            266 |
| Toys                   |        4.404 |           2682 |
| Watches                |        4.213 |            362 |
| Shoes                  |        4.187 |            699 |
| Camera                 |        4.155 |           1671 |
| Musical Instruments    |        4.127 |            229 |

**a2_step3_age_by_review_count** — [`sql/additional/a2_step3_age_by_review_count.sql`](../sql/additional/a2_step3_age_by_review_count.sql) · 47 rows · 329 ms

|   age |   review_count |
|------:|---------------:|
|    38 |           4195 |
|    41 |           4186 |
|    22 |           4025 |
|    44 |           3964 |
|    61 |           3946 |
|    34 |           3847 |
|    42 |           3840 |
|    51 |           3830 |
|    18 |           3817 |
|    50 |           3814 |

**a3_step2_information_schema_amazon_reviews** — [`sql/additional/a3_step2_information_schema_amazon_reviews.sql`](../sql/additional/a3_step2_information_schema_amazon_reviews.sql) · 1 rows · 16 ms

| table_schema     | table_name     | table_type   |
|:-----------------|:---------------|:-------------|
| review_analytics | amazon_reviews | VIEW         |

※ ローカルでは CSV を VIEW として登録しているため table_type は `VIEW`。Athena では Glue の外部テーブルとして `BASE TABLE` が返る。

- `a1_step1_female_categories.sql`: 86,678 rows (194 ms)
- `a1_step2_female_categories_grouped.sql`: 30 rows (195 ms)
- `a2_step1_age.sql`: 170,296 rows (192 ms)
- `a2_step2_age_grouped.sql`: 47 rows (182 ms)
- `a3_step1_information_schema.sql`: 2 rows (2 ms)

## ハンズオン4: Bedrock 出力とのJOIN（ギャップ検知）

`data/ai_reviews_output.jsonl` が無いためスキップ（Bedrock を呼んだ実出力を置くと同じSQLで集計される）。