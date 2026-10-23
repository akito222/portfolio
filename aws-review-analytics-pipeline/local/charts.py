"""Static PNG charts that stand in for the Amazon Quick visuals (for the README)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import logging  # noqa: E402

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

BLUE = "#2a78d6"
BLUE_LIGHT = "#86b6ef"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
SURFACE = "#fcfcfb"

plt.rcParams.update(
    {
        "font.family": ["Noto Sans CJK JP", "Hiragino Sans", "Yu Gothic", "IPAexGothic", "sans-serif"],
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": "#c3c2b7",
        "axes.labelcolor": INK_2,
        "xtick.color": MUTED,
        "ytick.color": INK_2,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.titleweight": "bold",
        "axes.titlesize": 12,
        "axes.titlecolor": INK,
        "axes.titlelocation": "left",
        "axes.axisbelow": True,
    }
)


def _shorten(s: str, n: int = 34) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def hbar(
    df: pd.DataFrame,
    label: str,
    value: str,
    title: str,
    xlabel: str,
    path: Path,
    fmt: str = "{:,.0f}",
    highlight_first: bool = False,
) -> None:
    d = df.iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 0.42 * len(d) + 1.2))
    colors = [BLUE] * len(d)
    if highlight_first:
        colors = [BLUE_LIGHT] * (len(d) - 1) + [BLUE]
    bars = ax.barh([_shorten(x) for x in d[label]], d[value], color=colors, height=0.62)
    ax.grid(axis="y", visible=False)
    ax.set_axisbelow(True)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    for b, v in zip(bars, d[value]):
        ax.text(
            b.get_width(), b.get_y() + b.get_height() / 2, " " + fmt.format(v), va="center", fontsize=8, color=INK_2
        )
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def render_all(r: dict[str, pd.DataFrame], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)

    t = r["top10"].copy()
    t["customer_id"] = t["customer_id"].astype(str)
    hbar(t, "customer_id", "count_review", "レビュー数が多いお客様 Top10", "レビュー数", out / "h1_top10_customers.png")

    hbar(
        r["titles"],
        "product_title",
        "reviews",
        "レビュー件数が多い商品 Top10",
        "レビュー件数",
        out / "h1_top_titles.png",
    )

    # share of distinct products per category: a sorted bar reads better than a pie
    c = r["cat_products"].copy()
    top = c.head(8)
    other = pd.DataFrame(
        [{"product_category": f"その他 ({len(c) - 8} カテゴリ)", "products": c["products"].iloc[8:].sum()}]
    )
    c = pd.concat([top, other], ignore_index=True)
    c["share"] = c["products"] / c["products"].sum() * 100
    hbar(
        c, "product_category", "share", "カテゴリ別の商品種数の割合", "%", out / "h1_category_share.png", fmt="{:.1f}%"
    )

    s = r["scan"].copy()
    s["MB"] = s["bytes"] / 1024 / 1024
    labels = ["CSV 全体", "Parquet 全体", "Parquet Books のみ", "Parquet Books・2列"]
    s["label"] = labels
    # values span ~4 orders of magnitude -> log axis, labelled as such
    fig, ax = plt.subplots(figsize=(8, 2.8))
    d = s.iloc[::-1]
    bars = ax.barh(d["label"], d["MB"], color=[BLUE, BLUE_LIGHT, BLUE_LIGHT, BLUE_LIGHT][::-1], height=0.6)
    ax.set_xscale("log")
    ax.grid(axis="y", visible=False)
    ax.set_title("Books クエリで読むデータ量（対数軸）")
    ax.set_xlabel("MB（対数軸）")
    for b, v, pct in zip(bars, d["MB"], d["CSV比"]):
        ax.text(
            b.get_width(), b.get_y() + b.get_height() / 2, f" {v:,.2f} MB ({pct})", va="center", fontsize=8, color=INK_2
        )
    fig.tight_layout()
    fig.savefig(out / "h3_scan_bytes.png", dpi=150)
    plt.close(fig)

    f = r["a1_extra_female_categories_reliable"].copy()
    fig, ax = plt.subplots(figsize=(8, 0.42 * len(f) + 1.2))
    d = f.iloc[::-1]
    bars = ax.barh(d["product_category"], d["avg_rating"], color=BLUE, height=0.62)
    lo = max(0, d["avg_rating"].min() - 0.3)
    ax.set_xlim(lo, 5)
    ax.grid(axis="y", visible=False)
    ax.set_title("女性レビューの平均★（レビュー100件以上のカテゴリ）")
    ax.set_xlabel(f"平均★（軸は {lo:.1f} から）")
    for b, v, n in zip(bars, d["avg_rating"], d["review_count"]):
        ax.text(
            b.get_width(), b.get_y() + b.get_height() / 2, f" {v:.2f}  (n={n:,})", va="center", fontsize=8, color=INK_2
        )
    fig.tight_layout()
    fig.savefig(out / "a1_female_avg_rating.png", dpi=150)
    plt.close(fig)

    a = r["a2_step3_age_by_review_count"].dropna().sort_values("age")
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.bar(a["age"], a["review_count"], color=BLUE, width=0.8)
    ax.grid(axis="x", visible=False)
    ax.set_title("年齢別レビュー数")
    ax.set_xlabel("年齢")
    ax.set_ylabel("レビュー数")
    peak = a.loc[a["review_count"].idxmax()]
    ax.set_ylim(0, a["review_count"].max() * 1.18)
    ax.annotate(
        f"最多 {int(peak['age'])}歳: {int(peak['review_count']):,}件",
        (peak["age"], peak["review_count"]),
        textcoords="offset points",
        xytext=(0, 6),
        ha="center",
        fontsize=8,
        color=INK_2,
    )
    fig.tight_layout()
    fig.savefig(out / "a2_age_review_count.png", dpi=150)
    plt.close(fig)
