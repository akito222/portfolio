"""
Day3: Transformerを自前実装して、超ミニ言語モデルを学習させる
=================================================================
講座Day3の目標：「言語モデルにおけるTransformerの位置づけ」「Transformerの構造」
「事前学習のパイプライン」を、実際に手を動かして理解する。

・文字単位(character-level)のTiny Shakespeare的データで学習
・Self-Attention / Multi-Head Attention / Positional Encoding を全部スクラッチで書く
・Google ColabでもローカルUbuntu(RTX 5060等)でもそのまま動く

実行方法:
    python day3_transformer.py
  もしくはColabでセルにコピペして実行
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F

torch.manual_seed(42)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# -----------------------------------------------------------------
# 1. データ準備（超シンプルなトイデータ。好きな.txtに差し替え可能）
# -----------------------------------------------------------------
text = """日本の首都は東京です。東京は世界有数の大都市です。
言語モデルは次に来る単語を予測する確率モデルです。
Transformerはself-attentionを中心にしたネットワーク構造です。
大規模言語モデルは大量のテキストデータで事前学習されます。
""" * 50  # 繰り返してデータ量を確保（デモ用）

chars = sorted(list(set(text)))
vocab_size = len(chars)
stoi = {ch: i for i, ch in enumerate(chars)}
itos = {i: ch for i, ch in enumerate(chars)}

def encode(s):
    return [stoi[c] for c in s]

def decode(ids):
    return "".join(itos[i] for i in ids)

data = torch.tensor(encode(text), dtype=torch.long)
n = int(0.9 * len(data))
train_data, val_data = data[:n], data[n:]

block_size = 32   # 一度に見る文脈の長さ（Day1でいう L）
batch_size = 16

def get_batch(split):
    d = train_data if split == "train" else val_data
    ix = torch.randint(len(d) - block_size - 1, (batch_size,))
    x = torch.stack([d[i:i + block_size] for i in ix])
    y = torch.stack([d[i + 1:i + block_size + 1] for i in ix])  # 1つずらしたのが正解（next token prediction）
    return x.to(device), y.to(device)


# -----------------------------------------------------------------
# 2. Transformerの部品（Day3スライドの構造をそのままコード化）
# -----------------------------------------------------------------

class PositionalEncoding(nn.Module):
    """単語の「並び順」情報をembeddingに足し込む（Day3: Positional Encoding）"""
    def __init__(self, d_model, max_len=512):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x):
        return x + self.pe[:, :x.size(1), :]


class SelfAttentionHead(nn.Module):
    """1つのAttention head（Day3: Self-Attention）
    「文中のどの単語が、どの単語と強く関係しているか」をQuery/Key/Valueで計算する
    """
    def __init__(self, d_model, head_size):
        super().__init__()
        self.key = nn.Linear(d_model, head_size, bias=False)
        self.query = nn.Linear(d_model, head_size, bias=False)
        self.value = nn.Linear(d_model, head_size, bias=False)
        self.register_buffer("tril", torch.tril(torch.ones(block_size, block_size)))

    def forward(self, x):
        B, T, C = x.shape
        k = self.key(x)
        q = self.query(x)
        # QとKの内積で「関係の強さ(スコア)」を計算 → softmaxで確率化
        wei = q @ k.transpose(-2, -1) * (C ** -0.5)
        # 未来の単語を見えなくする（GPTのような自己回帰生成のためのマスク）
        wei = wei.masked_fill(self.tril[:T, :T] == 0, float("-inf"))
        wei = F.softmax(wei, dim=-1)
        v = self.value(x)
        out = wei @ v
        return out


class MultiHeadAttention(nn.Module):
    """複数のheadを並列に使う（Day3: Multi-Head Attention）
    → 違う「視点」で単語同士の関係を同時に見られる
    """
    def __init__(self, d_model, n_heads):
        super().__init__()
        head_size = d_model // n_heads
        self.heads = nn.ModuleList([SelfAttentionHead(d_model, head_size) for _ in range(n_heads)])
        self.proj = nn.Linear(d_model, d_model)

    def forward(self, x):
        out = torch.cat([h(x) for h in self.heads], dim=-1)
        return self.proj(out)


class FeedForward(nn.Module):
    """Attentionの後に通す全結合層（各単語ごとに独立に処理）"""
    def __init__(self, d_model):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_model, 4 * d_model),
            nn.GELU(),
            nn.Linear(4 * d_model, d_model),
        )

    def forward(self, x):
        return self.net(x)


class TransformerBlock(nn.Module):
    """Attention + FeedForward を1ブロックにまとめたもの。これを何層も積む"""
    def __init__(self, d_model, n_heads):
        super().__init__()
        self.attn = MultiHeadAttention(d_model, n_heads)
        self.ff = FeedForward(d_model)
        self.ln1 = nn.LayerNorm(d_model)
        self.ln2 = nn.LayerNorm(d_model)

    def forward(self, x):
        x = x + self.attn(self.ln1(x))   # 残差接続（勾配消失を防ぐ）
        x = x + self.ff(self.ln2(x))
        return x


class TinyGPT(nn.Module):
    """Day3のまとめ：GPT的な自己回帰言語モデル
    Embedding + PositionalEncoding → TransformerBlock×N → 語彙への線形変換
    """
    def __init__(self, vocab_size, d_model=64, n_heads=4, n_layers=3):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab_size, d_model)
        self.pos_enc = PositionalEncoding(d_model, max_len=block_size)
        self.blocks = nn.Sequential(*[TransformerBlock(d_model, n_heads) for _ in range(n_layers)])
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size)

    def forward(self, idx, targets=None):
        x = self.tok_emb(idx)
        x = self.pos_enc(x)
        x = self.blocks(x)
        x = self.ln_f(x)
        logits = self.head(x)  # (B, T, vocab_size) 各位置での「次の単語」の確率分布(の元)

        loss = None
        if targets is not None:
            B, T, V = logits.shape
            loss = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))
        return logits, loss

    @torch.no_grad()
    def generate(self, idx, max_new_tokens=100):
        for _ in range(max_new_tokens):
            idx_cond = idx[:, -block_size:]
            logits, _ = self(idx_cond)
            logits = logits[:, -1, :]  # 最後の位置＝「次に来る単語」の予測
            probs = F.softmax(logits, dim=-1)
            next_id = torch.multinomial(probs, num_samples=1)  # 確率的にサンプリング
            idx = torch.cat([idx, next_id], dim=1)
        return idx


# -----------------------------------------------------------------
# 3. 事前学習ループ（Day3: 「自己教師あり学習で次の単語を予測」を実際にやる）
# -----------------------------------------------------------------
model = TinyGPT(vocab_size).to(device)
print(f"パラメータ数: {sum(p.numel() for p in model.parameters()):,}")

optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3)

for step in range(500):
    xb, yb = get_batch("train")
    logits, loss = model(xb, yb)
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    optimizer.step()

    if step % 100 == 0:
        model.eval()
        with torch.no_grad():
            xv, yv = get_batch("val")
            _, val_loss = model(xv, yv)
        model.train()
        print(f"step {step:4d} | train loss {loss.item():.3f} | val loss {val_loss.item():.3f}")

# -----------------------------------------------------------------
# 4. 生成してみる（学習した「次の単語予測」を使って文章を作る）
# -----------------------------------------------------------------
context = torch.zeros((1, 1), dtype=torch.long, device=device)  # 空文字から生成開始
generated = model.generate(context, max_new_tokens=200)
print("\n--- 生成結果 ---")
print(decode(generated[0].tolist()))
