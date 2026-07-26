"""
Day8: 学習データの整備と評価ベンチマーク ー ミニ実装
=================================================================
講座Day8の目標：
 ・学習データの整備技術（品質フィルタ・重複除去）を説明できる
 ・評価ベンチマークの資源・手法を説明・実装できる
 ・大規模言語モデルの性能評価を実装できる

【この実験の3本立て】
 1. Perplexity（評価指標）を実装して、良いモデル/悪いモデルを数値で区別する
 2. MinHash による重複除去（dedup）を実装する
 3. データ汚染（contamination）が評価をどう歪めるかを実演する

実行方法:
    python day8/day8_data_and_eval.py
"""

import math
import random
import hashlib
import torch
import torch.nn as nn
import torch.nn.functional as F

random.seed(8)
torch.manual_seed(8)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}\n")

# =================================================================
# パート1: Perplexity（評価指標）
# =================================================================
print("=" * 60)
print("パート1: Perplexity（言語モデルの評価指標）")
print("=" * 60)
print("""
Perplexity(パープレキシティ)とは:
  「モデルが次の単語をどれだけ迷わずに当てられるか」を表す指標。
  PPL = exp(平均クロスエントロピー損失)
  ・低いほど良い（＝迷いが少ない＝良いモデル）
  ・PPL=1 は完璧、PPL=語彙数 はランダム当てずっぽうと同じ
""")

# 簡単なモデルを用意（Day3と同じ構造の縮小版）
text = "言語モデルは次に来る単語を予測する。" * 100
chars = sorted(set(text))
stoi = {c: i for i, c in enumerate(chars)}
vocab_size = len(chars)
data = torch.tensor([stoi[c] for c in text], device=device)
block_size = 16


class MiniLM(nn.Module):
    def __init__(self, vocab_size, d=32):
        super().__init__()
        self.emb = nn.Embedding(vocab_size, d)
        self.pos = nn.Embedding(block_size, d)
        self.lstm = nn.LSTM(d, d, batch_first=True)
        self.head = nn.Linear(d, vocab_size)

    def forward(self, x):
        h = self.emb(x) + self.pos(torch.arange(x.size(1), device=x.device))
        h, _ = self.lstm(h)
        return self.head(h)


def get_batch():
    ix = torch.randint(0, len(data) - block_size - 1, (32,), device=device)
    x = torch.stack([data[i:i + block_size] for i in ix])
    y = torch.stack([data[i + 1:i + block_size + 1] for i in ix])
    return x, y


@torch.no_grad()
def perplexity(model):
    model.eval()
    losses = []
    for _ in range(20):
        x, y = get_batch()
        logits = model(x)
        loss = F.cross_entropy(logits.view(-1, vocab_size), y.view(-1))
        losses.append(loss.item())
    model.train()
    avg_loss = sum(losses) / len(losses)
    return math.exp(avg_loss)


model = MiniLM(vocab_size).to(device)
print(f"学習前のPerplexity: {perplexity(model):8.2f}  (語彙数={vocab_size}に近い＝当てずっぽう)")

opt = torch.optim.AdamW(model.parameters(), lr=5e-3)
for step in range(300):
    x, y = get_batch()
    loss = F.cross_entropy(model(x).view(-1, vocab_size), y.view(-1))
    opt.zero_grad(); loss.backward(); opt.step()

print(f"学習後のPerplexity: {perplexity(model):8.2f}  (1に近いほど良いモデル)")

# =================================================================
# パート2: MinHash による重複除去(dedup)
# =================================================================
print("\n" + "=" * 60)
print("パート2: MinHash による重複除去（データ整備）")
print("=" * 60)
print("""
なぜ重複除去が必要？:
  ネットから集めた文章には、ほぼ同じ文が大量にある(コピペ記事など)。
  同じ文を何度も学習するとモデルが偏る＆無駄。
  → MinHashで「似ている文章ペア」を効率よく見つけて消す。
  MinHashは Jaccard係数(集合の重なり具合)を高速に推定する手法。
""")


def ngrams(text, n=3):
    """文字n-gramの集合を作る"""
    return set(text[i:i + n] for i in range(len(text) - n + 1))


def jaccard(a, b):
    """正確なJaccard係数（答え合わせ用）"""
    sa, sb = ngrams(a), ngrams(b)
    return len(sa & sb) / len(sa | sb) if sa | sb else 0.0


def minhash_signature(text, num_hashes=64, n=3):
    """MinHash署名：num_hashes個のハッシュ関数それぞれの最小値を並べたもの"""
    grams = ngrams(text, n)
    sig = []
    for seed in range(num_hashes):
        min_h = min(
            int(hashlib.md5(f"{seed}_{g}".encode()).hexdigest(), 16) for g in grams
        ) if grams else 0
        sig.append(min_h)
    return sig


def estimated_jaccard(sig_a, sig_b):
    """2つのMinHash署名が一致する割合 ≈ Jaccard係数"""
    matches = sum(1 for a, b in zip(sig_a, sig_b) if a == b)
    return matches / len(sig_a)


documents = [
    "言語モデルは次に来る単語を予測する確率モデルです",
    "言語モデルは次に来る単語を予測する確率モデルだ",       # ↑とほぼ重複
    "Transformerはattentionを中心にした構造です",
    "今日は良い天気ですね散歩に行きましょう",
    "Transformerはアテンションを中心とした構造です",       # ↑Transformer文とやや類似
]

print("文書ペアの類似度（正確なJaccard vs MinHash推定）:")
print(f"{'ペア':<8}{'正確なJaccard':>16}{'MinHash推定':>16}")
sigs = [minhash_signature(d) for d in documents]
threshold = 0.5
duplicates = []
for i in range(len(documents)):
    for j in range(i + 1, len(documents)):
        exact = jaccard(documents[i], documents[j])
        est = estimated_jaccard(sigs[i], sigs[j])
        mark = "  ← 重複と判定" if est >= threshold else ""
        print(f"({i},{j})    {exact:>14.3f}{est:>16.3f}{mark}")
        if est >= threshold:
            duplicates.append((i, j))

print(f"\n重複除去の結果: {len(duplicates)}組の重複ペアを検出")
print("→ 実際のRefinedWeb等では、これを数十億文書規模で高速に実行してデータを掃除する")

# =================================================================
# パート3: データ汚染(contamination)の実演
# =================================================================
print("\n" + "=" * 60)
print("パート3: データ汚染（contamination）が評価を歪める実演")
print("=" * 60)
print("""
データ汚染とは:
  評価用ベンチマークの問題を、うっかり学習データに混ぜてしまうこと。
  → モデルは"答えを暗記"しているだけなのに、テストで高得点に見える。
  正しい評価には「学習に使っていない問題」でテストする必要がある。
""")

# ベンチマーク問題
benchmark_q = "日本の首都は"
benchmark_a = "東京"

# ケースA: クリーンな学習（ベンチマークを含まない）
clean_text = "言語モデルは単語を予測する。機械学習は面白い。" * 80
# ケースB: 汚染された学習（ベンチマークの答えを混入）
dirty_text = clean_text + (benchmark_q + benchmark_a + "。") * 80


def train_and_eval_on_benchmark(train_text, label):
    ch = sorted(set(train_text + benchmark_q + benchmark_a))
    s2i = {c: i for i, c in enumerate(ch)}
    vs = len(ch)
    dat = torch.tensor([s2i[c] for c in train_text], device=device)
    bs = 12

    class TinyLSTM(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = nn.Embedding(vs, 32)
            self.lstm = nn.LSTM(32, 32, batch_first=True)
            self.head = nn.Linear(32, vs)

        def forward(self, x):
            h = self.emb(x); h, _ = self.lstm(h); return self.head(h)

    m = TinyLSTM().to(device)
    o = torch.optim.AdamW(m.parameters(), lr=5e-3)
    for _ in range(300):
        ix = torch.randint(0, len(dat) - bs - 1, (32,), device=device)
        x = torch.stack([dat[i:i + bs] for i in ix])
        y = torch.stack([dat[i + 1:i + bs + 1] for i in ix])
        loss = F.cross_entropy(m(x).view(-1, vs), y.view(-1))
        o.zero_grad(); loss.backward(); o.step()

    # ベンチマークで評価：「日本の首都は」の次に「東京」を当てられるか
    m.eval()
    with torch.no_grad():
        prompt = torch.tensor([[s2i[c] for c in benchmark_q]], device=device)
        logits = m(prompt)[0, -1]
        pred = ch[torch.argmax(logits).item()]
        prob_correct = F.softmax(logits, dim=-1)[s2i[benchmark_a[0]]].item()
    print(f"[{label}]")
    print(f"  「{benchmark_q}」の次の予測: 「{pred}」")
    print(f"  正解「{benchmark_a[0]}」の予測確率: {prob_correct:.4f}")
    return prob_correct


p_clean = train_and_eval_on_benchmark(clean_text, "クリーン学習（ベンチマーク未混入）")
p_dirty = train_and_eval_on_benchmark(dirty_text, "汚染学習（ベンチマーク混入）")

print(f"\n→ 正解確率: クリーン {p_clean:.4f}  vs  汚染 {p_dirty:.4f}")
print("  汚染した方が不当に高得点になる ＝ これがデータ汚染の怖さ。")
print("  だからベンチマークは『学習に使っていない問題』で作る必要がある。")
