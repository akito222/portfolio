"""
Day2 実験: デコーディング設定と Self-Consistency の効果を数値とグラフで確かめる
=================================================================
実行: python day2/experiment.py   （CPU で数十秒）
出力: day2/results/*.png と day2/results/results.md

グラフの文字は環境によって日本語フォントが無いことがあるため英語にしている。
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from sampling import (entropy, greedy, sample, self_consistency_accuracy, softmax,
                      top_k_filter, top_p_filter)

OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)

# 「ペットとして飼うなら ___」の次トークン候補を想定したトイ logits
TOKENS = ["cat", "dog", "bird", "fish", "desk", "cloud", "stone", "shoe"]
LOGITS = np.array([4.0, 3.2, 2.5, 1.0, 0.5, 0.0, -0.5, -1.0])
NONSENSE = {"desk", "cloud", "stone", "shoe"}  # 文脈的におかしい候補

md = ["# Day2 実験結果", "", "`python day2/experiment.py` が自動生成するファイルです。", ""]


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return lines


# -----------------------------------------------------------------
# 実験1: 温度で分布の形がどう変わるか
# -----------------------------------------------------------------
temps = [0.5, 1.0, 2.0]
fig, axes = plt.subplots(1, len(temps), figsize=(12, 3.2), sharey=True)
rows = []
for ax, t in zip(axes, temps):
    p = softmax(LOGITS, t)
    ax.bar(TOKENS, p, color=["#3b82f6" if w not in NONSENSE else "#ef4444" for w in TOKENS])
    ax.set_title(f"T = {t}  (entropy {entropy(p):.2f})")
    ax.tick_params(axis="x", rotation=45)
    rows.append([t, f"{p[0]:.3f}", f"{sum(p[i] for i, w in enumerate(TOKENS) if w in NONSENSE):.3f}",
                 f"{entropy(p):.2f}"])
axes[0].set_ylabel("probability")
fig.suptitle("Temperature reshapes the next-token distribution (red = nonsense tokens)")
fig.tight_layout()
fig.savefig(OUT / "temperature.png", dpi=120)
plt.close(fig)

md += ["## 実験1: 温度と分布の形", "", "![temperature](temperature.png)", ""]
md += table(["温度 T", "最有力 cat の確率", "文脈的におかしい 4 語の合計確率", "エントロピー"], rows)
md += ["", "温度を上げるほど分布が平らになり、おかしな候補にも確率が回ってくる。", ""]

# -----------------------------------------------------------------
# 実験2: Top-k と Top-p で「残る候補の数」はどう違うか
# -----------------------------------------------------------------
peaked = softmax(np.array([6.0, 2.0, 1.5, 1.0, 0.5, 0.0, -0.5, -1.0]))  # 自信がある場面
flat = softmax(np.array([1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6, 0.5]))      # 迷っている場面
ps = np.linspace(0.5, 0.99, 30)
fig, ax = plt.subplots(figsize=(6, 3.5))
ax.plot(ps, [np.count_nonzero(top_p_filter(peaked, p)) for p in ps], label="top-p, peaked dist.")
ax.plot(ps, [np.count_nonzero(top_p_filter(flat, p)) for p in ps], label="top-p, flat dist.")
ax.axhline(3, color="gray", ls="--", label="top-k (k=3), any dist.")
ax.set_xlabel("p")
ax.set_ylabel("# candidate tokens kept")
ax.legend()
ax.set_title("Top-p adapts the candidate set to the model's confidence")
fig.tight_layout()
fig.savefig(OUT / "top_p_vs_top_k.png", dpi=120)
plt.close(fig)

rows = [[name, np.count_nonzero(top_k_filter(d, 3)), np.count_nonzero(top_p_filter(d, 0.9))]
        for name, d in [("尖った分布（自信あり）", peaked), ("平らな分布（迷っている）", flat)]]
md += ["## 実験2: Top-k と Top-p の違い", "", "![top-p](top_p_vs_top_k.png)", ""]
md += table(["分布", "Top-k (k=3) で残る候補数", "Top-p (p=0.9) で残る候補数"], rows)
md += ["", "Top-k は分布の形に関係なく常に k 個。Top-p は自信がある場面では絞り、迷う場面では広げる。", ""]

# -----------------------------------------------------------------
# 実験3: 設定ごとに 1 万回サンプリングして多様性と「事故率」を比べる
# -----------------------------------------------------------------
rng = np.random.default_rng(0)
settings = [("Greedy", None), ("T=1.0", dict(temperature=1.0)), ("T=1.5", dict(temperature=1.5)),
            ("T=1.5 + top-k=3", dict(temperature=1.5, top_k=3)),
            ("T=1.5 + top-p=0.9", dict(temperature=1.5, top_p=0.9))]
rows = []
for name, kw in settings:
    if kw is None:
        draws = [greedy(LOGITS)] * 10_000
    else:
        draws = [sample(LOGITS, rng=rng, **kw) for _ in range(10_000)]
    used = len(set(draws))
    bad = np.mean([TOKENS[d] in NONSENSE for d in draws])
    rows.append([name, used, f"{bad * 100:.2f}%"])
md += ["## 実験3: 多様性と「おかしな語」を選ぶ率（各 1 万回）", ""]
md += table(["設定", "出現したトークンの種類", "おかしな語を選んだ率"], rows)
md += ["", "高温にすると多様になるが、おかしな語を選ぶ率も上がる。Top-k (k=3) は裾を完全に切るので 0% になった。",
       "Top-p (p=0.9) は半分以下に減らしたが 0 にはならない。温度で分布が平らになると、p=0.9 に届くまでに必要な候補が増えるため。",
       "Top-p は温度をかけた後の分布に対して働くので、温度との組み合わせで効き方が変わる。", ""]

# -----------------------------------------------------------------
# 実験4: Self-Consistency（多数決）の効果
# -----------------------------------------------------------------
ns = [1, 3, 5, 9, 15, 25]
cases = [(0.3, 4, "p=0.3, wrong answers scattered (4 kinds)"),
         (0.5, 4, "p=0.5, wrong answers scattered (4 kinds)"),
         (0.4, 1, "p=0.4, wrong answers concentrated (1 kind)")]
fig, ax = plt.subplots(figsize=(6.5, 3.8))
rows = []
for p, k, label in cases:
    accs = [self_consistency_accuracy(p, n, n_wrong=k, trials=2000, seed=1) for n in ns]
    ax.plot(ns, accs, marker="o", label=label)
    rows.append([f"p={p}, 誤答 {k} 種類"] + [f"{a:.2f}" for a in accs])
ax.set_xlabel("# sampled reasoning paths (N)")
ax.set_ylabel("accuracy after majority vote")
ax.set_ylim(0, 1.02)
ax.legend(fontsize=8)
ax.set_title("Self-Consistency helps only when errors disagree")
fig.tight_layout()
fig.savefig(OUT / "self_consistency.png", dpi=120)
plt.close(fig)

md += ["## 実験4: Self-Consistency（多数決）の効果", "", "![self-consistency](self_consistency.png)", ""]
md += table(["1 回あたりの正解率と誤答の種類"] + [f"N={n}" for n in ns], rows)
md += ["", "1 回の正解率が 30% でも、誤答がばらけていれば多数決で正解率が上がる。",
       "逆に誤答が 1 種類に集中していると、多数決はその誤答を強めてしまう。", ""]

(OUT / "results.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
