"""
Day4: スケール則(Scaling Law)を自分で求める
=================================================================
講座Day4の目標：
 ・スケール則とはなにか、その重要性を説明できる
 ・スケール則の具体的な求め方を説明・実装できる
 ・PyTorchでスケール則を実際に求めるコードを実装する

【スケール則とは】
 モデルサイズ N、データ量 D、計算量 C を増やすと、
 損失 L が「べき乗則(Power-Law)」に従って下がる、という経験則。

     L(X) = (Xc / X)^alpha        (X は N, D, C のいずれか)

 両辺の log をとると：
     log L = -alpha * log X + alpha * log Xc

 → 両対数グラフ上で「直線」になる。傾きが -alpha。
 これがKaplan+ 2020 "Scaling Laws for Neural Language Models" の中心的発見。

【この実験でやること】
 モデルサイズ N を変えながら Tiny Transformer を複数学習させ、
 (N, L) の組を集めて両対数プロットし、直線フィットで alpha を求める。

実行方法:
    python day4/day4_scaling_law.py
"""

import math
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import matplotlib
matplotlib.use("Agg")  # GUIなし環境でも保存できるように
import matplotlib.pyplot as plt

torch.manual_seed(0)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# -----------------------------------------------------------------
# 1. データ（Day3より少し多様なテキストにする。実験の質を上げるため）
# -----------------------------------------------------------------
base_text = """言語モデルは次に来る単語を予測する確率モデルである。
Transformerはself-attentionを中心にしたネットワーク構造である。
大規模言語モデルは大量のテキストデータで事前学習される。
スケール則はモデルサイズとデータ量と計算量に関する経験則である。
日本の首都は東京であり、世界有数の大都市として知られている。
機械学習では損失関数を最小化するようにパラメータを更新していく。
勾配降下法は損失の勾配方向にパラメータを少しずつ動かす手法である。
自己回帰モデルは過去のトークン列から次のトークンを生成していく。
注意機構はクエリとキーの内積によって関連度を計算する仕組みである。
事前学習の後にファインチューニングを行うことで下流タスクに適応する。
強化学習では報酬を最大化するように方策を最適化していく。
ベンチマークによって言語モデルの性能を定量的に評価することができる。
"""
text = base_text * 80

chars = sorted(list(set(text)))
vocab_size = len(chars)
stoi = {ch: i for i, ch in enumerate(chars)}
data = torch.tensor([stoi[c] for c in text], dtype=torch.long)
n = int(0.9 * len(data))
train_data, val_data = data[:n], data[n:]
print(f"語彙サイズ: {vocab_size}, 総トークン数: {len(data):,}")

block_size = 32
batch_size = 32


def get_batch(split):
    d = train_data if split == "train" else val_data
    ix = torch.randint(len(d) - block_size - 1, (batch_size,))
    x = torch.stack([d[i:i + block_size] for i in ix])
    y = torch.stack([d[i + 1:i + block_size + 1] for i in ix])
    return x.to(device), y.to(device)


# -----------------------------------------------------------------
# 2. モデル定義（Day3と同じ構造。サイズだけ変えられるようにする）
# -----------------------------------------------------------------
class Block(nn.Module):
    def __init__(self, d_model, n_heads):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, n_heads, batch_first=True)
        self.ff = nn.Sequential(
            nn.Linear(d_model, 4 * d_model), nn.GELU(), nn.Linear(4 * d_model, d_model)
        )
        self.ln1, self.ln2 = nn.LayerNorm(d_model), nn.LayerNorm(d_model)
        mask = torch.triu(torch.ones(block_size, block_size), diagonal=1).bool()
        self.register_buffer("mask", mask)

    def forward(self, x):
        h = self.ln1(x)
        T = x.size(1)
        a, _ = self.attn(h, h, h, attn_mask=self.mask[:T, :T], need_weights=False)
        x = x + a
        x = x + self.ff(self.ln2(x))
        return x


class TinyGPT(nn.Module):
    def __init__(self, vocab_size, d_model, n_heads, n_layers):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab_size, d_model)
        self.pos_emb = nn.Embedding(block_size, d_model)
        self.blocks = nn.Sequential(*[Block(d_model, n_heads) for _ in range(n_layers)])
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size)

    def forward(self, idx, targets=None):
        B, T = idx.shape
        pos = torch.arange(T, device=idx.device)
        x = self.tok_emb(idx) + self.pos_emb(pos)
        x = self.blocks(x)
        logits = self.head(self.ln_f(x))
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.view(B * T, -1), targets.view(B * T))
        return logits, loss


def count_non_embedding_params(model):
    """スケール則の N は通常 embedding を除いたパラメータ数を使う(Kaplan+ 2020の流儀)"""
    total = sum(p.numel() for p in model.parameters())
    emb = model.tok_emb.weight.numel() + model.pos_emb.weight.numel()
    return total - emb


@torch.no_grad()
def estimate_loss(model, n_eval=50):
    model.eval()
    losses = []
    for _ in range(n_eval):
        x, y = get_batch("val")
        _, loss = model(x, y)
        losses.append(loss.item())
    model.train()
    return float(np.mean(losses))


def train_one(d_model, n_heads, n_layers, steps=800, lr=3e-3):
    model = TinyGPT(vocab_size, d_model, n_heads, n_layers).to(device)
    N = count_non_embedding_params(model)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    for step in range(steps):
        x, y = get_batch("train")
        _, loss = model(x, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
    final_loss = estimate_loss(model)
    return N, final_loss


# -----------------------------------------------------------------
# 3. モデルサイズを変えて複数学習 → (N, L) を集める
# -----------------------------------------------------------------
configs = [
    # (d_model, n_heads, n_layers)
    (16, 2, 1),
    (24, 2, 2),
    (32, 4, 2),
    (48, 4, 3),
    (64, 4, 4),
    (96, 6, 4),
    (128, 8, 5),
]

Ns, Ls = [], []
print("\n=== モデルサイズを変えて学習 ===")
for (d, h, l) in configs:
    N, L = train_one(d, h, l)
    Ns.append(N)
    Ls.append(L)
    print(f"d_model={d:4d} layers={l} | N(non-emb)={N:>9,} | val loss={L:.4f}")

Ns = np.array(Ns, dtype=float)
Ls = np.array(Ls, dtype=float)

# -----------------------------------------------------------------
# 4. べき乗則フィット: log L = -alpha * log N + const
# -----------------------------------------------------------------
logN, logL = np.log(Ns), np.log(Ls)
slope, intercept = np.polyfit(logN, logL, 1)
alpha = -slope
Nc = math.exp(intercept / alpha)  # L = (Nc/N)^alpha の Nc

print("\n=== フィット結果 ===")
print(f"傾き (両対数上) = {slope:.4f}")
print(f"alpha_N        = {alpha:.4f}")
print(f"Nc             = {Nc:.4e}")
print(f"→ スケール則: L(N) = (Nc / N)^alpha = ({Nc:.3e} / N)^{alpha:.4f}")
print(f"\n【参考】Kaplan+ 2020 の実測値は alpha_N ≈ 0.076")
print("   （今回は極小データ・極小モデルなので値は一致しません。")
print("     「両対数で直線に乗る」という性質そのものを確認するのが目的です）")

# 外挿の例：スケール則の使い方（大きいモデルの性能を事前に予測する）
for target_N in [1e6, 1e7]:
    pred = (Nc / target_N) ** alpha
    print(f"外挿予測: N={target_N:.0e} のとき L ≈ {pred:.4f}")

# -----------------------------------------------------------------
# 5. プロット
# -----------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

axes[0].plot(Ns, Ls, "o-", color="tab:blue")
axes[0].set_xlabel("N (non-embedding parameters)")
axes[0].set_ylabel("Validation Loss")
axes[0].set_title("Linear scale")
axes[0].grid(alpha=0.3)

axes[1].loglog(Ns, Ls, "o", color="tab:blue", label="measured")
fit_N = np.logspace(np.log10(Ns.min()), np.log10(Ns.max()), 100)
fit_L = np.exp(intercept) * fit_N ** slope
axes[1].loglog(fit_N, fit_L, "--", color="tab:red",
               label=f"fit: L = (Nc/N)^{alpha:.3f}")
axes[1].set_xlabel("N (non-embedding parameters)  [log]")
axes[1].set_ylabel("Validation Loss  [log]")
axes[1].set_title("Log-log scale: straight line = power law")
axes[1].legend()
axes[1].grid(alpha=0.3, which="both")

plt.tight_layout()
out = "outputs/day4_scaling_law.png"
plt.savefig(out, dpi=120)
print(f"\nグラフを保存しました: {out}")
