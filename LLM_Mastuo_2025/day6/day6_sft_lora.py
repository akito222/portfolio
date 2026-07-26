"""
Day6: Instruction Tuning (SFT) と PEFT (LoRA) を自前実装
=================================================================
講座Day6の目標：
 ・Instruction Tuning が事前学習と何が違うか説明できる
 ・PEFT (LoRA) がなぜ効率的か説明できる
 ・SFTとLoRAをコードで実装できる

【この実験の流れ】
 1. Day3と同じTinyGPTを「事前学習」する（次の単語予測のみ。QAができない状態を再現）
 2. その状態で質問しても、まともに答えられないことを確認する
 3. 「質問→回答」ペアのデータでInstruction Tuning (SFT) する
    → Full-FT（全パラメータ更新）と LoRA（一部だけ効率よく更新）の両方を試す
 4. 学習パラメータ数・挙動の変化を比較する

実行方法:
    python day6/day6_sft_lora.py
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F

torch.manual_seed(1)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# -----------------------------------------------------------------
# 1. データ準備
# -----------------------------------------------------------------
# 事前学習用：ふつうの文章（「次の単語予測」だけを学ぶ）
pretrain_text = """言語モデルは次に来る単語を予測する確率モデルです。
日本の首都は東京です。東京は世界有数の大都市です。
Transformerはself-attentionを中心にしたネットワーク構造です。
大規模言語モデルは大量のテキストデータで事前学習されます。
""" * 60

# Instruction Tuning用：「質問→回答」のペア（SFTデータ）
# <Q>質問<A>回答<EOS> という形式で学習させる
qa_pairs = [
    ("日本の首都は?", "東京です。"),
    ("Transformerの中心的な仕組みは?", "self-attentionです。"),
    ("言語モデルは何を予測する?", "次に来る単語を予測します。"),
    ("大規模言語モデルは何で学習される?", "大量のテキストデータで学習されます。"),
] * 40

# 語彙は両方のデータから作る
all_text = pretrain_text + "".join(q + a for q, a in qa_pairs) + "<Q><A><EOS><PAD>"
chars = sorted(list(set(all_text)))
# 特殊トークンを追加（実際には複数文字だが、簡単のため1文字トークンとして予約枠を用意）
specials = ["<Q>", "<A>", "<EOS>", "<PAD>"]
vocab = specials + [c for c in chars if c not in specials]
stoi = {t: i for i, t in enumerate(vocab)}
itos = {i: t for t, i in stoi.items()}
vocab_size = len(vocab)
print(f"語彙サイズ(特殊トークン込み): {vocab_size}")


def tokenize(s):
    """雑だが分かりやすいトークナイザ：<Q><A><EOS>は1トークン、それ以外は1文字1トークン"""
    ids = []
    i = 0
    while i < len(s):
        matched = False
        for sp in specials:
            if s[i:i + len(sp)] == sp:
                ids.append(stoi[sp])
                i += len(sp)
                matched = True
                break
        if not matched:
            ids.append(stoi[s[i]])
            i += 1
    return ids


def detok(ids):
    return "".join(itos[i] for i in ids)


block_size = 48
batch_size = 16
PAD_ID = stoi["<PAD>"]
EOS_ID = stoi["<EOS>"]


# -----------------------------------------------------------------
# 2. モデル定義（LoRA対応版のLinear層を用意する）
# -----------------------------------------------------------------
class LoRALinear(nn.Module):
    """通常のLinear層 + LoRAの低ランク行列 A, B
    y = Wx + (alpha/r) * B(A(x))
    ・W（元の重み）は凍結（更新しない）
    ・A, B だけを学習する → これがPEFTの核心
    """
    def __init__(self, in_features, out_features, r=4, alpha=8, bias=True):
        super().__init__()
        self.base = nn.Linear(in_features, out_features, bias=bias)
        self.r = r
        self.scaling = alpha / r
        # A: d_in × r,  B: r × d_out  （講義スライドの表記通り）
        self.lora_A = nn.Parameter(torch.randn(in_features, r) * 0.01)
        self.lora_B = nn.Parameter(torch.zeros(r, out_features))  # Bはゼロ初期化(講義資料の通り)
        self.lora_enabled = False

    def freeze_base(self):
        for p in self.base.parameters():
            p.requires_grad = False

    def forward(self, x):
        out = self.base(x)
        if self.lora_enabled:
            out = out + self.scaling * (x @ self.lora_A @ self.lora_B)
        return out


class Block(nn.Module):
    def __init__(self, d_model, n_heads, use_lora=False):
        super().__init__()
        self.n_heads = n_heads
        self.d_model = d_model
        # Attentionの q,k,v,proj を全部LoRA対応Linearにしておく
        self.qkv = LoRALinear(d_model, 3 * d_model, bias=False)
        self.proj = LoRALinear(d_model, d_model, bias=False)
        self.ff1 = LoRALinear(d_model, 4 * d_model)
        self.ff2 = LoRALinear(4 * d_model, d_model)
        self.ln1, self.ln2 = nn.LayerNorm(d_model), nn.LayerNorm(d_model)
        mask = torch.triu(torch.ones(block_size, block_size), diagonal=1).bool()
        self.register_buffer("mask", mask)

    def forward(self, x):
        B, T, C = x.shape
        h = self.ln1(x)
        qkv = self.qkv(h).view(B, T, 3, self.n_heads, C // self.n_heads)
        q, k, v = qkv.unbind(2)
        q, k, v = [t.transpose(1, 2) for t in (q, k, v)]  # (B, nh, T, hd)
        att = (q @ k.transpose(-2, -1)) * (1.0 / math.sqrt(q.size(-1)))
        att = att.masked_fill(self.mask[:T, :T], float("-inf"))
        att = F.softmax(att, dim=-1)
        out = (att @ v).transpose(1, 2).contiguous().view(B, T, C)
        x = x + self.proj(out)
        h2 = self.ln2(x)
        x = x + self.ff2(F.gelu(self.ff1(h2)))
        return x

    def all_lora_linears(self):
        return [self.qkv, self.proj, self.ff1, self.ff2]


class TinyGPT(nn.Module):
    def __init__(self, vocab_size, d_model=64, n_heads=4, n_layers=4):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab_size, d_model)
        self.pos_emb = nn.Embedding(block_size, d_model)
        self.blocks = nn.ModuleList([Block(d_model, n_heads) for _ in range(n_layers)])
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size)

    def forward(self, idx, targets=None):
        B, T = idx.shape
        pos = torch.arange(T, device=idx.device)
        x = self.tok_emb(idx) + self.pos_emb(pos)
        for blk in self.blocks:
            x = blk(x)
        logits = self.head(self.ln_f(x))
        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)), targets.view(-1), ignore_index=PAD_ID
            )
        return logits, loss

    @torch.no_grad()
    def generate(self, idx, max_new_tokens=20):
        for _ in range(max_new_tokens):
            idx_cond = idx[:, -block_size:]
            logits, _ = self(idx_cond)
            next_id = torch.argmax(logits[:, -1, :], dim=-1, keepdim=True)
            idx = torch.cat([idx, next_id], dim=1)
            if next_id.item() == EOS_ID:
                break
        return idx

    def set_lora(self, enabled: bool):
        for blk in self.blocks:
            for lin in blk.all_lora_linears():
                lin.lora_enabled = enabled

    def freeze_base_params(self):
        for blk in self.blocks:
            for lin in blk.all_lora_linears():
                lin.freeze_base()

    def lora_parameters(self):
        params = []
        for blk in self.blocks:
            for lin in blk.all_lora_linears():
                params += [lin.lora_A, lin.lora_B]
        return params


def count_trainable(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def count_total(model):
    return sum(p.numel() for p in model.parameters())


# -----------------------------------------------------------------
# 3. ステップ1: 事前学習（次の単語予測のみ）
# -----------------------------------------------------------------
def make_batch(token_ids_list):
    """可変長シーケンスのリストからバッチを作る（右パディング）"""
    xs, ys = [], []
    for ids in token_ids_list:
        ids = ids[:block_size + 1]
        ids = ids + [PAD_ID] * (block_size + 1 - len(ids))
        xs.append(ids[:-1])
        ys.append(ids[1:])
    return torch.tensor(xs, device=device), torch.tensor(ys, device=device)


pretrain_ids = tokenize(pretrain_text)


def get_pretrain_batch():
    seqs = []
    for _ in range(batch_size):
        start = torch.randint(0, len(pretrain_ids) - block_size - 1, (1,)).item()
        seqs.append(pretrain_ids[start:start + block_size + 1])
    xs = torch.tensor([s[:-1] for s in seqs], device=device)
    ys = torch.tensor([s[1:] for s in seqs], device=device)
    return xs, ys


model = TinyGPT(vocab_size).to(device)
print(f"\n総パラメータ数: {count_total(model):,}")

print("\n=== ステップ1: 事前学習（次の単語予測のみ） ===")
opt = torch.optim.AdamW(model.parameters(), lr=3e-3)
for step in range(400):
    x, y = get_pretrain_batch()
    _, loss = model(x, y)
    opt.zero_grad(set_to_none=True)
    loss.backward()
    opt.step()
    if step % 100 == 0:
        print(f"step {step:4d} | pretrain loss {loss.item():.3f}")

# -----------------------------------------------------------------
# 4. 事前学習だけの状態で質問してみる（→まともに答えられないはず）
# -----------------------------------------------------------------
def ask(model, question):
    model.eval()
    prompt = tokenize(f"<Q>{question}<A>")
    idx = torch.tensor([prompt], device=device)
    out = model.generate(idx, max_new_tokens=20)
    model.train()
    return detok(out[0].tolist())

print("\n=== 事前学習のみの状態で質問してみる ===")
print(ask(model, "日本の首都は?"))
print("→ 質問に答える、という行動そのものを知らないので支離滅裂になるはず")

# -----------------------------------------------------------------
# 5. ステップ2: Instruction Tuning (SFT)
# -----------------------------------------------------------------
sft_sequences = [tokenize(f"<Q>{q}<A>{a}<EOS>") for q, a in qa_pairs]


def get_sft_batch():
    idxs = torch.randint(0, len(sft_sequences), (batch_size,))
    batch = [sft_sequences[i] for i in idxs]
    return make_batch(batch)


def run_sft(model, steps=300, lr=1e-3, label=""):
    for step in range(steps):
        x, y = get_sft_batch()
        _, loss = model(x, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        if step % 100 == 0:
            print(f"[{label}] step {step:4d} | SFT loss {loss.item():.3f}")


import copy

# --- 5a. Full-FT（全パラメータを更新） ---
model_fullft = copy.deepcopy(model)
print(f"\n=== ステップ2a: Full-FT (Instruction Tuning, 全パラメータ更新) ===")
print(f"学習対象パラメータ数: {count_trainable(model_fullft):,} / 全体 {count_total(model_fullft):,}")
opt = torch.optim.AdamW(model_fullft.parameters(), lr=1e-3)
run_sft(model_fullft, steps=300, label="Full-FT")

print("\n--- Full-FT後の質問応答 ---")
for q, _ in qa_pairs[:4]:
    print(f"Q: {q}")
    print(f"A: {ask(model_fullft, q)}")

# --- 5b. LoRA（一部だけ効率よく更新） ---
model_lora = copy.deepcopy(model)
model_lora.freeze_base_params()   # 元の重みを凍結
model_lora.set_lora(True)         # LoRA経路を有効化

# base（凍結済み）以外を全部凍結する。学習対象はLoRAのA,Bとheadのみに絞る例
for p in model_lora.parameters():
    p.requires_grad = False
for p in model_lora.lora_parameters():
    p.requires_grad = True

print(f"\n=== ステップ2b: LoRA (PEFT, 一部パラメータのみ更新) ===")
n_trainable = count_trainable(model_lora)
n_total = count_total(model_lora)
print(f"学習対象パラメータ数: {n_trainable:,} / 全体 {n_total:,}  ({100*n_trainable/n_total:.2f}%)")

opt = torch.optim.AdamW(model_lora.lora_parameters(), lr=3e-3)
run_sft(model_lora, steps=300, label="LoRA")

print("\n--- LoRA後の質問応答 ---")
for q, _ in qa_pairs[:4]:
    print(f"Q: {q}")
    print(f"A: {ask(model_lora, q)}")

# -----------------------------------------------------------------
# 6. まとめ比較
# -----------------------------------------------------------------
print("\n=== Full-FT vs LoRA 比較まとめ ===")
print(f"Full-FT 学習対象パラメータ: {count_trainable(model_fullft):,} (100%)")
print(f"LoRA    学習対象パラメータ: {n_trainable:,} ({100*n_trainable/n_total:.2f}%)")
print("→ ずっと少ないパラメータ更新でも、質問応答ができるようになっていれば")
print("  「PEFT/LoRAは効率よく振る舞いを変えられる」という講義の主張を体感できたことになります")
