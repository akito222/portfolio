"""
Day6 深掘り: LoRAの完全理解 ― ランクrの影響 & 重みマージの実演
=================================================================
【この深掘り実験で確認すること】
 1. LoRAのランク r を変えると、性能とパラメータ数がどうトレードオフするか
 2. 「Bをゼロ初期化する」となぜ学習開始時に増分ΔW=0になるかをコードで確認
 3. 推論時に ΔW = (alpha/r)*BA を元の重みにマージすると、
    LoRA層を通常のLinearに戻せる（＝推論オーバーヘッドがゼロになる）ことを実証

前提: day6_sft_lora.py と同じディレクトリ構成で動く独立スクリプト
実行:  python day6/day6_lora_deepdive.py
"""

import copy
import torch
import torch.nn as nn
import torch.nn.functional as F

torch.manual_seed(6)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}\n")

# -----------------------------------------------------------------
# 0. データ（Day6と同じ QA タスク）
# -----------------------------------------------------------------
pretrain_text = """言語モデルは次に来る単語を予測する確率モデルです。
日本の首都は東京です。Transformerはattentionの構造です。
""" * 60
qa_pairs = [
    ("日本の首都は?", "東京です。"),
    ("Transformerの仕組みは?", "attentionです。"),
    ("言語モデルは何を予測?", "次の単語を予測します。"),
] * 40

specials = ["<Q>", "<A>", "<EOS>", "<PAD>"]
raw = pretrain_text + "".join(q + a for q, a in qa_pairs) + "".join(specials)
chars = sorted(set(raw))
vocab = specials + [c for c in chars if c not in specials]
stoi = {t: i for i, t in enumerate(vocab)}
itos = {i: t for t, i in stoi.items()}
vocab_size = len(vocab)
PAD_ID, EOS_ID = stoi["<PAD>"], stoi["<EOS>"]
block_size, batch_size = 40, 16


def tokenize(s):
    ids, i = [], 0
    while i < len(s):
        m = False
        for sp in specials:
            if s[i:i+len(sp)] == sp:
                ids.append(stoi[sp]); i += len(sp); m = True; break
        if not m:
            ids.append(stoi[s[i]]); i += 1
    return ids


def detok(ids): return "".join(itos[i] for i in ids)


# -----------------------------------------------------------------
# 1. LoRA対応Linear（マージ機能つき）
# -----------------------------------------------------------------
class LoRALinear(nn.Module):
    def __init__(self, in_f, out_f, r=4, alpha=8, bias=False):
        super().__init__()
        self.base = nn.Linear(in_f, out_f, bias=bias)
        self.r, self.scaling = r, alpha / r
        self.lora_A = nn.Parameter(torch.randn(in_f, r) * 0.02)
        self.lora_B = nn.Parameter(torch.zeros(r, out_f))  # ゼロ初期化 → 開始時ΔW=0
        self.enabled = True
        self.merged = False

    def delta_w(self):
        """増分重み ΔW = (alpha/r) * A @ B  （形は in_f × out_f）"""
        return self.scaling * (self.lora_A @ self.lora_B)

    def forward(self, x):
        out = self.base(x)
        if self.enabled and not self.merged:
            out = out + self.scaling * (x @ self.lora_A @ self.lora_B)
        return out

    @torch.no_grad()
    def merge(self):
        """ΔWを元の重みに足し込む → 以降はbaseだけで同じ出力（推論高速化）
        nn.Linearの重みは (out_f, in_f) なので delta_w()を転置して足す"""
        self.base.weight.data += self.delta_w().T
        self.merged = True

    @torch.no_grad()
    def unmerge(self):
        self.base.weight.data -= self.delta_w().T
        self.merged = False


class Block(nn.Module):
    def __init__(self, d, h, r):
        super().__init__()
        self.h = h
        self.qkv = LoRALinear(d, 3*d, r=r)
        self.proj = LoRALinear(d, d, r=r)
        self.ff1 = LoRALinear(d, 4*d, r=r)
        self.ff2 = LoRALinear(4*d, d, r=r)
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.register_buffer("mask", torch.triu(torch.ones(block_size, block_size), 1).bool())

    def forward(self, x):
        B, T, C = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, C//self.h).unbind(2)
        q, k, v = [t.transpose(1, 2) for t in (q, k, v)]
        att = (q @ k.transpose(-2, -1)) * (C//self.h)**-0.5
        att = att.masked_fill(self.mask[:T, :T], float("-inf")).softmax(-1)
        o = (att @ v).transpose(1, 2).reshape(B, T, C)
        x = x + self.proj(o)
        x = x + self.ff2(F.gelu(self.ff1(self.ln2(x))))
        return x

    def lora_layers(self): return [self.qkv, self.proj, self.ff1, self.ff2]


class TinyGPT(nn.Module):
    def __init__(self, r=4, d=64, h=4, L=4):
        super().__init__()
        self.tok = nn.Embedding(vocab_size, d)
        self.pos = nn.Embedding(block_size, d)
        self.blocks = nn.ModuleList([Block(d, h, r) for _ in range(L)])
        self.lnf = nn.LayerNorm(d)
        self.head = nn.Linear(d, vocab_size)

    def forward(self, idx):
        T = idx.size(1)
        x = self.tok(idx) + self.pos(torch.arange(T, device=idx.device))
        for b in self.blocks:
            x = b(x)
        return self.head(self.lnf(x))

    def all_lora(self):
        return [l for b in self.blocks for l in b.lora_layers()]

    @torch.no_grad()
    def generate(self, idx, n=15):
        for _ in range(n):
            logits = self(idx[:, -block_size:])
            nxt = logits[:, -1].argmax(-1, keepdim=True)
            idx = torch.cat([idx, nxt], 1)
            if nxt.item() == EOS_ID: break
        return idx


def make_batch(seqs):
    xs, ys = [], []
    for ids in seqs:
        ids = (ids[:block_size+1] + [PAD_ID]*(block_size+1))[:block_size+1]
        xs.append(ids[:-1]); ys.append(ids[1:])
    return torch.tensor(xs, device=device), torch.tensor(ys, device=device)


pre_ids = tokenize(pretrain_text)
sft_seqs = [tokenize(f"<Q>{q}<A>{a}<EOS>") for q, a in qa_pairs]


def ask(m, q):
    m.eval()
    out = m.generate(torch.tensor([tokenize(f"<Q>{q}<A>")], device=device))
    m.train()
    return detok(out[0].tolist())


# -----------------------------------------------------------------
# 2. 実験1: 「Bゼロ初期化 → 開始時ΔW=0」をコードで確認
# -----------------------------------------------------------------
print("="*60)
print("実験1: Bゼロ初期化により、学習開始時の増分ΔWがゼロであることを確認")
print("="*60)
probe = TinyGPT(r=4).to(device)
layer0 = probe.all_lora()[0]
print(f"lora_A のノルム: {layer0.lora_A.norm().item():.4f}  (正規乱数なので非ゼロ)")
print(f"lora_B のノルム: {layer0.lora_B.norm().item():.4f}  (ゼロ初期化なのでゼロ)")
print(f"増分ΔW のノルム: {layer0.delta_w().norm().item():.6f}  (A×B=0 なのでゼロ)")
print("→ 学習開始時点では元の事前学習モデルと完全に同じ挙動から始まる\n")

# -----------------------------------------------------------------
# 3. 事前学習＋SFT を、ランクrを変えて実行（実験2）
# -----------------------------------------------------------------
def build_and_pretrain(r):
    m = TinyGPT(r=r).to(device)
    # まず全体を軽く事前学習（baseにも学習させて土台を作る）
    for l in m.all_lora():
        l.enabled = False  # 事前学習中はLoRA無効（baseだけ動かす）
    opt = torch.optim.AdamW(m.parameters(), lr=3e-3)
    for _ in range(250):
        s = torch.randint(0, len(pre_ids)-block_size-1, (batch_size,)).tolist()
        x, y = make_batch([pre_ids[i:i+block_size+1] for i in s])
        loss = F.cross_entropy(m(x).reshape(-1, vocab_size), y.reshape(-1), ignore_index=PAD_ID)
        opt.zero_grad(); loss.backward(); opt.step()
    return m


def sft_with_lora(m, r):
    # baseを凍結、LoRAだけ学習
    for p in m.parameters():
        p.requires_grad = False
    for l in m.all_lora():
        l.enabled = True
        l.lora_A.requires_grad = True
        l.lora_B.requires_grad = True
    lora_params = [l.lora_A for l in m.all_lora()] + [l.lora_B for l in m.all_lora()]
    n_trainable = sum(p.numel() for p in lora_params)
    opt = torch.optim.AdamW(lora_params, lr=5e-3)
    final = 0
    for _ in range(300):
        idx = torch.randint(0, len(sft_seqs), (batch_size,))
        x, y = make_batch([sft_seqs[i] for i in idx])
        loss = F.cross_entropy(m(x).reshape(-1, vocab_size), y.reshape(-1), ignore_index=PAD_ID)
        opt.zero_grad(); loss.backward(); opt.step()
        final = loss.item()
    return n_trainable, final


print("="*60)
print("実験2: LoRAのランク r を変えて、性能とパラメータ数のトレードオフを見る")
print("="*60)
base_model = build_and_pretrain(4)  # 土台を1つ作って使い回す

results = []
for r in [1, 2, 4, 8, 16]:
    m = copy.deepcopy(base_model)
    # ランクrに合わせてLoRA行列を作り直す
    for blk in m.blocks:
        for name in ["qkv", "proj", "ff1", "ff2"]:
            old = getattr(blk, name)
            in_f = old.lora_A.shape[0]
            out_f = old.lora_B.shape[1]
            new = LoRALinear(in_f, out_f, r=r).to(device)
            new.base = old.base  # 事前学習済みのbaseを引き継ぐ
            setattr(blk, name, new)
    n_train, loss = sft_with_lora(m, r)
    acc = sum(1 for q, a in qa_pairs[:3] if a.rstrip("。") in ask(m, q)) / 3
    results.append((r, n_train, loss, acc))
    print(f"r={r:2d} | 学習パラメータ {n_train:>7,} | SFT loss {loss:.3f} | 簡易正答率 {acc:.2f}")

print("\n→ rを上げると表現力(学習パラメータ)は増えるが、簡単なタスクでは")
print("  小さいrでも十分。実務では『必要最小限のr』を探すのが定石。\n")

# -----------------------------------------------------------------
# 4. 実験3: 重みマージ ― LoRAを元の重みに足し込むと出力が一致
# -----------------------------------------------------------------
print("="*60)
print("実験3: 推論時マージ ― ΔWをbaseに足すとLoRA層が不要になる（高速化）")
print("="*60)
m = copy.deepcopy(base_model)
_, _ = sft_with_lora(m, 4)
m.eval()

test_q = "日本の首都は?"
x = torch.tensor([tokenize(f"<Q>{test_q}<A>")], device=device)

with torch.no_grad():
    out_before = m(x)[0, -1].clone()
    # マージ実行
    for l in m.all_lora():
        l.merge()
    out_after = m(x)[0, -1].clone()

diff = (out_before - out_after).abs().max().item()
print(f"マージ前後の出力の最大差: {diff:.2e}")
print("→ ほぼゼロ（数値誤差レベル）。マージしても出力は同一。")
print("  マージ後はΔW計算(x@A@B)が消え、通常のLinearと同じ計算量で推論できる。")
print("  これがLoRAの『推論オーバーヘッドなし』という最大の実務的利点。")
