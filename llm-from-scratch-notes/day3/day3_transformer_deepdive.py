"""
Day3 深掘り: Transformerの数式の「なぜ」を完全理解する
=================================================================
【4つの実験】
 実験1: なぜ sqrt(d_k) で割るのか ― 内積の分散が次元に比例することを実測
 実験2: sqrt(d_k)で割らないとsoftmaxが飽和し勾配が消えることを確認
 実験3: Multi-Head Attentionが「複数の視点」を持つ意味
 実験4: 残差接続(residual)とLayerNormが深いネットの学習を安定させる効果

実行: python day3/day3_transformer_deepdive.py
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F

torch.manual_seed(3)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}\n")

# =================================================================
# 実験1: 内積の分散が次元 d_k に比例することを実測
# =================================================================
print("="*62)
print("実験1: なぜ sqrt(d_k) で割るのか ― 内積の分散を実測")
print("="*62)
print("""
QとKの各成分が平均0・分散1のとき、内積 q・k = Σ q_i*k_i の分散は
理論上 d_k になる（独立な項の和の分散は項数に比例）。
これを実際にサンプリングして確かめる。
""")

print(f"{'次元 d_k':>10}{'内積の分散(実測)':>18}{'sqrt(d_k)で割った後':>22}")
for d_k in [4, 16, 64, 256, 1024]:
    # 平均0分散1のQ, Kを大量に作って内積の分散を測る
    q = torch.randn(10000, d_k)
    k = torch.randn(10000, d_k)
    dot = (q * k).sum(dim=1)                      # 各行の内積
    dot_scaled = dot / math.sqrt(d_k)             # sqrt(d_k)で割る
    print(f"{d_k:>10}{dot.var().item():>18.2f}{dot_scaled.var().item():>22.3f}")

print("\n→ 内積の分散は d_k とほぼ一致（理論通り）。")
print("  sqrt(d_k)で割ると、どの次元でも分散≈1に正規化される。\n")

# =================================================================
# 実験2: スケーリングしないとsoftmaxが飽和し勾配が消える
# =================================================================
print("="*62)
print("実験2: スケーリングなしだとsoftmaxが飽和 → 勾配消失")
print("="*62)
print("""
内積の分散が大きい(=値が極端)と、softmaxの出力がほぼ0か1になる。
すると勾配がほぼ0になり学習が進まない。これを数値で確認する。
""")

d_k = 64
q = torch.randn(1, d_k)
k = torch.randn(8, d_k)   # 8個のkeyに対するattention

# スケーリングなし
scores_raw = (q @ k.T).squeeze()
attn_raw = F.softmax(scores_raw, dim=-1)
# スケーリングあり
scores_scaled = scores_raw / math.sqrt(d_k)
attn_scaled = F.softmax(scores_scaled, dim=-1)

print(f"スケーリングなしのattention重み:\n  {attn_raw.numpy().round(4)}")
print(f"  最大値: {attn_raw.max().item():.4f}  エントロピー: {-(attn_raw*attn_raw.log()).sum().item():.3f}")
print(f"\nスケーリングありのattention重み:\n  {attn_scaled.numpy().round(4)}")
print(f"  最大値: {attn_scaled.max().item():.4f}  エントロピー: {-(attn_scaled*attn_scaled.log()).sum().item():.3f}")

# 勾配の大きさを比較
def grad_norm_after_softmax(scores):
    s = scores.clone().requires_grad_(True)
    out = F.softmax(s, dim=-1)
    out.sum().backward()  # ダミーの損失
    # softmaxの入力に対する勾配の大きさ（本当はもっと複雑だが傾向を見る）
    s2 = scores.clone().requires_grad_(True)
    loss = -(F.log_softmax(s2, dim=-1)[0])  # 1番目を正解とみなした損失
    loss.backward()
    return s2.grad.abs().mean().item()

g_raw = grad_norm_after_softmax(scores_raw)
g_scaled = grad_norm_after_softmax(scores_scaled)
print(f"\n勾配の平均大きさ:")
print(f"  スケーリングなし: {g_raw:.5f}  (小さい＝勾配消失気味)")
print(f"  スケーリングあり: {g_scaled:.5f}  (十分な大きさ)")
print("→ エントロピーが高い(=重みが分散している)方が勾配も健全。")
print("  sqrt(d_k)で割ることで学習可能な状態を保っている。\n")

# =================================================================
# 実験3: Multi-Head Attention ― 複数の視点
# =================================================================
print("="*62)
print("実験3: Multi-Head Attention ― なぜ複数ヘッドに分けるのか")
print("="*62)
print("""
1つの大きなAttention(1ヘッド)より、小さいAttentionを複数(マルチヘッド)にする。
各ヘッドが異なる関係性(例:文法的な係り受け / 意味的な関連)を担当できる。
ここでは、2つのヘッドが異なる単語ペアに注目する様子を可視化する。
""")

# トイ文: 「猫 が 魚 を 食べる」
words = ["猫", "が", "魚", "を", "食べる"]
T, d = len(words), 16
x = torch.randn(T, d)

n_heads = 2
head_dim = d // n_heads

# 2つのヘッドで異なる重みを使う（ランダムだが別々の視点になる）
for head in range(n_heads):
    torch.manual_seed(100 + head)
    Wq = torch.randn(d, head_dim) * 0.5
    Wk = torch.randn(d, head_dim) * 0.5
    q = x @ Wq
    k = x @ Wk
    attn = F.softmax((q @ k.T) / math.sqrt(head_dim), dim=-1)
    # 各単語が最も注目している相手
    print(f"ヘッド{head+1}: 各単語が最も注目する相手")
    for i, w in enumerate(words):
        focus = words[attn[i].argmax().item()]
        print(f"  「{w}」→「{focus}」に注目 (重み{attn[i].max().item():.2f})")
    print()

print("→ ヘッドごとに注目パターンが違う。実際のLLMでは、あるヘッドは")
print("  主語-動詞、別のヘッドは修飾関係、というように分業が生まれる。\n")

# =================================================================
# 実験4: 残差接続とLayerNormの効果
# =================================================================
print("="*62)
print("実験4: 残差接続(residual)とLayerNormが深いネットを安定させる")
print("="*62)
print("""
Transformerは何十層も積む。層を深くすると、信号(activation)が
指数的に増大/減衰しやすい。残差接続とLayerNormがこれを防ぐ。
各層での信号の大きさが、深さとともにどう変化するかを追う。
""")

def track_activations(depth=50, use_residual=True, use_norm=True, seed=0):
    torch.manual_seed(seed)
    d = 32
    x = torch.randn(1, d)
    layers = [torch.randn(d, d) * 0.4 for _ in range(depth)]  # 固定のランダム重み
    norm = nn.LayerNorm(d)
    mags = []
    for W in layers:
        h = torch.tanh(x @ W)
        if use_residual:
            x = x + h
        else:
            x = h
        if use_norm:
            x = norm(x)
        mags.append(x.abs().mean().item())
    return mags

configs = [
    (False, False, "残差なし・Normなし"),
    (True,  False, "残差あり・Normなし"),
    (True,  True,  "残差あり・Normあり(=Transformer)"),
]

print(f"{'構成':40s}{'1層目':>10}{'10層目':>10}{'25層目':>10}{'50層目':>10}")
print("-"*80)
for use_res, use_norm, label in configs:
    m = track_activations(depth=50, use_residual=use_res, use_norm=use_norm)
    print(f"{label:38s}{m[0]:>10.3f}{m[9]:>10.3f}{m[24]:>10.3f}{m[49]:>10.3f}")

print("""
→ 各構成での信号の推移:
  ・残差なし・Normなし → tanh飽和で信号がほぼ一定の小さい値に潰れる
    (層を重ねても情報が育たず、深くする意味が薄れる)
  ・残差あり・Normなし → 信号が層ごとに積み上がり、どんどん増大
    (放置すると爆発。だから正規化が要る)
  ・残差あり・Normあり → 信号が一定の健全な範囲に保たれる
    これが『Transformerを何十層も安定して積める』理由。
""")

print("【補足】残差接続の勾配的な意味:")
print("  y = x + f(x) の勾配は dy/dx = 1 + df/dx。")
print("  '+1' があるおかげで、f の勾配が小さくても勾配が完全には消えない。")
print("  これが深いネットで勾配が生き残る数学的な理由。")
