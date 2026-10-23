import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local"))

from databrew_local import apply_recipe, load_recipe  # noqa: E402

FIX = ROOT / "tests" / "fixtures"


def test_recipe_adds_expected_columns_and_values():
    df = pd.DataFrame(
        {
            "product_title": ["ABC", "Def"],
            "product_category": ["Books", "Books"],
            "product_id": ["p1", "p2"],
            "star_rating": [5, 3],
            "verified_purchase": ["Y", "N"],
        }
    )
    out = apply_recipe(df, load_recipe(ROOT / "databrew/recipe.json"))
    assert list(out["product_title_lower"]) == ["abc", "def"]
    assert list(out["category_star_rating_mean"]) == [4.0, 4.0]
    assert list(out["product_star_rating_mean"]) == [5.0, 3.0]
    assert list(out["verified_purchase_Yes"]) == [1, 0]
    assert list(out["verified_purchase_No"]) == [0, 1]
    assert len(out) == len(df)  # "group as new column" keeps every row


def test_recipe_reuse_gives_same_schema():
    steps = load_recipe(ROOT / "databrew/recipe.json")
    a = apply_recipe(pd.read_csv(FIX / "amazon_reviews_5.csv"), steps)
    b = apply_recipe(pd.read_csv(FIX / "amazon_reviews_add.csv"), steps)
    assert list(a.columns) == list(b.columns)


def test_local_pipeline_smoke(tmp_path):
    """Every SQL file in sql/ runs and the CSV / Parquet answers match."""
    cmd = [
        sys.executable,
        str(ROOT / "local/run_local.py"),
        "--data-dir",
        str(FIX),
        "--out",
        str(tmp_path),
        "--work",
        str(tmp_path / "work"),
        "--no-charts",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    report = (tmp_path / "local-results.md").read_text(encoding="utf-8")
    assert "出力スキーマ一致: **True**" in report
