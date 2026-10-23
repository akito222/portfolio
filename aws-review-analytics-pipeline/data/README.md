# data/

レビューデータ本体はサイズが大きい（各 150MB 前後）ため **Git には含めていません**（`.gitignore` 済み）。

| ファイル | 用途 | 置き場所（S3） |
|---|---|---|
| `amazon_reviews_5.csv` | メインデータ（170,296 件） | `raw/amazon_reviews/` |
| `amazon_reviews_add.csv` | レシピ再利用・自動化テスト用の追加データ（149,656 件） | `raw/amazon_reviews_add/` |
| `ai_reviews_output.jsonl` | （任意）Bedrock の実出力。置くとローカル再現でハンズオン4のSQLも実行される | `ai/ai_reviews_output/` |

Excel で受け取った場合は CSV に変換します。

```bash
python scripts/xlsx_to_csv.py amazon_reviews_5_csv.xlsx   data/amazon_reviews_5.csv
python scripts/xlsx_to_csv.py amazon_reviews_add_csv.xlsx data/amazon_reviews_add.csv
```

スキーマ（17列）: `marketplace, customer_id, gender, age, review_id, product_id, product_parent, product_title, product_category, star_rating, helpful_votes, total_votes, vine, verified_purchase, review_headline, review_body, review_date`

CI では `tests/fixtures/` の合成データ（数十行・テスト用に自作）を使います。
