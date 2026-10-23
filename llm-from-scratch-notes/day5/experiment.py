"""
Day5 実験: MoE・int8 量子化・Attention の計算量を数値とグラフで確かめる
=================================================================
実行: python day5/experiment.py   （CPU で 1〜2 分）
出力: day5/results/*.png と day5/results/results.md
"""

import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
import torch.nn.functional as F

from attention import naive_attention, n_scores, peak_score_bytes, tiled_attention, window_attention
from moe import MoELayer, active_params_per_token
from quantization import (make_activations, matmul_int8_mixed, matmul_int8_tensorwise,
                          matmul_int8_vectorwise, outlier_dims, relative_error)

torch.manual_seed(0)
OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)
md = ["# Day5 実験結果", "", "`python day5/experiment.py` が自動生成するファイルです。", ""]


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return lines


# =================================================================
# 実験1: MoE — パラメータ数と計算量、負荷分散損失の効果
# =================================================================
d, h = 32, 64
rows = []
for E in [1, 2, 4, 8, 16]:
    layer = MoELayer(d, h, n_experts=E, top_k=min(2, E))
    total = sum(p.numel() for p in layer.parameters())
    rows.append([E, min(2, E), f"{total:,}", f"{active_params_per_token(layer):,}"])
md += ["## 実験1-a: expert を増やしても 1 トークンの計算量は増えない", ""]
md += table(["expert 数", "top-k", "総パラメータ数", "1 トークンで使うパラメータ数"], rows)
md += ["", "総パラメータ（=知識を蓄える容量）は expert 数に比例して増えるが、"
           "1 トークンの計算に使うのは top-k 個分だけで一定。", ""]

# 4 つのクラスタからなる入力。クラスタごとに別の線形写像を学ぶ回帰タスク
centers = torch.randn(4, d) * 3
maps = torch.randn(4, d, d) / d ** 0.5


def batch(n=256):
    c = torch.randint(4, (n,))
    x = centers[c] + torch.randn(n, d)
    y = torch.einsum("nd,nde->ne", x, maps[c])
    return x, y


def train(aux_coef, steps=400, seed=0):
    torch.manual_seed(seed)
    layer = MoELayer(d, h, n_experts=4, top_k=1)
    opt = torch.optim.Adam(layer.parameters(), lr=3e-3)
    for _ in range(steps):
        x, y = batch()
        loss = F.mse_loss(layer(x), y) + aux_coef * layer.last_aux_loss
        opt.zero_grad()
        loss.backward()
        opt.step()
    with torch.no_grad():
        x, y = batch(2048)
        mse = F.mse_loss(layer(x), y).item()
        load = layer.expert_load().float()
    return mse, (load / load.sum()).tolist(), layer.last_aux_loss.item()


res = {name: train(c) for name, c in [("aux なし", 0.0), ("aux あり (係数 0.1)", 0.1)]}
fig, ax = plt.subplots(figsize=(6, 3.2))
for i, (name, (_, share, _)) in enumerate(res.items()):
    ax.bar([e + i * 0.4 for e in range(4)], share, width=0.4,
           label="no aux loss" if i == 0 else "with aux loss (0.1)")
ax.axhline(0.25, color="gray", ls="--", label="perfectly balanced")
ax.set_xticks([e + 0.2 for e in range(4)], [f"expert {e}" for e in range(4)])
ax.set_ylabel("share of tokens")
ax.legend(fontsize=8)
ax.set_title("Load-balancing loss spreads tokens across experts (top-1)")
fig.tight_layout()
fig.savefig(OUT / "moe_load.png", dpi=120)
plt.close(fig)

rows = [[name, f"{mse:.3f}", " / ".join(f"{s:.2f}" for s in share), f"{max(share):.2f}", f"{aux:.2f}"]
        for name, (mse, share, aux) in res.items()]
md += ["## 実験1-b: 負荷分散損失の効果（4 expert, top-1, 400 step）", "", "![moe](moe_load.png)", ""]
md += table(["設定", "テスト MSE", "各 expert の担当割合", "最大の担当割合", "負荷分散損失（1 が均等）"], rows)
md += ["", "負荷分散損失を入れると、担当割合が均等（0.25）に近づいた。",
       "ただしこの小さなタスクと 400 step の範囲では、テスト MSE は悪化した。"
       "負荷の均等化と精度はトレードオフになりうるので、係数は調整が必要（ここでは 1 つの seed のみ）。", ""]

# =================================================================
# 実験2: int8 量子化の誤差 — 外れ値があると何が起きるか
# =================================================================
n, k, m = 256, 512, 256
W = torch.randn(k, m) * 0.05
rows, errs = [], {"per-tensor": [], "vector-wise": [], "mixed (LLM.int8)": []}
n_out_list = [0, 1, 4, 16]
for n_out in n_out_list:
    X = make_activations(n, k, n_outlier_dims=n_out, seed=1)
    Y = X @ W
    e = {"per-tensor": relative_error(matmul_int8_tensorwise(X, W), Y),
         "vector-wise": relative_error(matmul_int8_vectorwise(X, W), Y),
         "mixed (LLM.int8)": relative_error(matmul_int8_mixed(X, W), Y)}
    for key in errs:
        errs[key].append(e[key])
    kept = int(outlier_dims(X).sum())
    rows.append([n_out] + [f"{e[key] * 100:.3f}%" for key in errs] + [f"{kept} / {k}"])

fig, ax = plt.subplots(figsize=(6.5, 3.5))
for i, (key, vals) in enumerate(errs.items()):
    ax.bar([j + i * 0.27 for j in range(len(n_out_list))], [v * 100 for v in vals], width=0.27, label=key)
ax.set_xticks([j + 0.27 for j in range(len(n_out_list))], [str(o) for o in n_out_list])
ax.set_xlabel("# outlier feature dimensions in X")
ax.set_ylabel("relative error of XW (%)")
ax.set_yscale("log")
ax.legend(fontsize=8)
ax.set_title("A few outlier dimensions ruin absmax int8")
fig.tight_layout()
fig.savefig(OUT / "int8_error.png", dpi=120)
plt.close(fig)

md += ["## 実験2: int8 量子化の誤差と外れ値", "", "![int8](int8_error.png)", ""]
md += table(["外れ値次元の数", "per-tensor", "vector-wise", "mixed (LLM.int8() 型)", "高精度で残した次元"], rows)
md += ["", "外れ値が 1 次元でも混ざると absmax の scale が引っ張られ、普通の値が粗く丸められて誤差が跳ね上がる。",
       "外れ値の次元だけを高精度で計算すると、残すのが 512 次元中わずか 1〜16 次元でも、誤差は外れ値なしのとき以下に収まった。",
       "注意: ここでの誤差は出力の大きさで割った相対誤差なので、外れ値で出力が大きくなったぶん小さく見える。"
       "外れ値の数が増えるほど per-tensor の誤差が下がって見えるのも同じ理由。", ""]

# =================================================================
# 実験3: Attention の計算量とメモリ
# =================================================================
dh = 64
Ts = [128, 256, 512, 1024, 2048]
rows, t_naive, t_tiled, t_window = [], [], [], []


def bench(fn, reps=3):
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return sorted(times)[len(times) // 2] * 1000


for T in Ts:
    q, k_, v = (torch.randn(T, dh) for _ in range(3))
    ref = naive_attention(q, k_, v)
    diff = (tiled_attention(q, k_, v, block=64) - ref).abs().max().item()
    t_naive.append(bench(lambda: naive_attention(q, k_, v)))
    t_tiled.append(bench(lambda: tiled_attention(q, k_, v, block=64)))
    t_window.append(bench(lambda: window_attention(q, k_, v, window=64)))
    rows.append([T, f"{n_scores(T, 'full'):,}", f"{n_scores(T, 'window'):,}",
                 f"{peak_score_bytes(T, 'naive') / 2**20:.2f} MiB", f"{peak_score_bytes(T, 'tiled') / 2**20:.3f} MiB",
                 f"{diff:.1e}", f"{t_naive[-1]:.1f}", f"{t_tiled[-1]:.1f}"])

fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
axes[0].loglog(Ts, [n_scores(T, "full") for T in Ts], "o-", label="full causal (~T^2/2)")
axes[0].loglog(Ts, [n_scores(T, "window") for T in Ts], "o-", label="sliding window w=64 (~T*w)")
axes[0].loglog(Ts, [peak_score_bytes(T, "naive") / 4 for T in Ts], "s--", label="naive: scores held at once (T^2)")
axes[0].loglog(Ts, [peak_score_bytes(T, "tiled") / 4 for T in Ts], "s--", label="tiled B=64: held at once (T*B)")
axes[0].set_xlabel("sequence length T")
axes[0].set_ylabel("# attention scores")
axes[0].legend(fontsize=7)
axes[0].set_title("Compute vs memory")
axes[1].loglog(Ts, t_naive, "o-", label="naive")
axes[1].loglog(Ts, t_tiled, "o-", label="tiled (pure PyTorch, not fused)")
axes[1].loglog(Ts, t_window, "o-", label="window (masked naive)")
axes[1].set_xlabel("sequence length T")
axes[1].set_ylabel("CPU time (ms, median of 3)")
axes[1].legend(fontsize=7)
axes[1].set_title("Wall-clock on this machine")
for ax in axes:
    ax.set_xticks(Ts, [str(T) for T in Ts])
    ax.minorticks_off()
fig.tight_layout()
fig.savefig(OUT / "attention_cost.png", dpi=120)
plt.close(fig)

md += ["## 実験3: Attention の計算量とメモリ（1 ヘッド、d=64）", "", "![attention](attention_cost.png)", ""]
md += table(["T", "因果 Attention のスコア数", "window (w=64) のスコア数", "naive が同時に持つスコア",
             "tiled (B=64) が同時に持つスコア", "naive との最大誤差", "naive [ms]", "tiled [ms]"], rows)
md += ["", "系列長を 2 倍にするとスコアの数は約 4 倍になる（T² に比例）。",
       "tiled は naive と同じ出力（誤差は float32 の丸め程度）を、T×T 行列を持たずに計算できる。",
       "ただし PyTorch の演算を並べただけなので速くはならない。FlashAttention の速さは、"
       "この計算を 1 つの GPU カーネルにまとめてメモリの読み書きを減らすことから来る。",
       "window のスコア数（T·w）は、ウィンドウ内だけを計算する専用カーネルの場合の値。"
       "ここでの window_attention は出力を確かめるために T×T 行列を作ってからマスクしているので、時間は naive と変わらない。",
       "時間の列は実行したマシンの CPU での値で、環境によって変わる。", ""]

(OUT / "results.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
