"""
Day7: 強化学習によるAlignment ー DPO (Direct Preference Optimization) 自前実装
=================================================================
講座Day7の目標：
 ・RLHF/DPO/GRPOの概要を説明できる
 ・「人間の好みに合わせる」とはどういうことか体感する
 ・DPOの損失関数を実装できる

【講義の流れ（かみくだくと）】
 RLHF（3ステップ）:
   Step1: SFT（Day6でやった "質問に答えられる" ようにする）
   Step2: 報酬モデルの学習（"どちらの回答がより好ましいか" を判定するモデルを作る）
   Step3: 強化学習（PPO）で、報酬が高くなるように方策(=LLM)を更新する

 DPO（Rafailov+ 2023 "Direct Preference Optimization"）:
   RLHFは「報酬モデルを作る→強化学習する」で2段階必要で複雑。
   DPOは "報酬モデルを作らずに、好み比較データから直接LLMを最適化" する手法。
   数式的には「RLHFの最適解 = DPOの損失を最小化した解」であることが示されている
   （講義スライド "DPOの理論 | RLHF = DPO"）。

   DPOの損失関数:
     L_DPO(theta) = -log sigmoid(
         beta * [ (log pi_theta(y_w|x) - log pi_ref(y_w|x))
                - (log pi_theta(y_l|x) - log pi_ref(y_l|x)) ]
     )
   y_w = 好ましい回答(chosen), y_l = 好ましくない回答(rejected)
   pi_ref = 学習前の方策（凍結。基準点として使う）
   pi_theta = 学習中の方策（これを更新する）

   直感：chosen の確率を ref より相対的に上げ、rejected の確率を相対的に下げる。

【この実験でやること】
 同じ質問に対して「丁寧な回答(chosen)」と「そっけない回答(rejected)」のペアを用意し、
 DPOで学習前後の生成確率がどう変化するかを確認する。

実行方法:
    python day7/day7_dpo.py
"""

import math
import copy
import torch
import torch.nn as nn
import torch.nn.functional as F

torch.manual_seed(7)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# -----------------------------------------------------------------
# 1. データ準備
# -----------------------------------------------------------------
pretrain_text = """言語モデルは次に来る単語を予測する確率モデルです。
日本の首都は東京です。東京は世界有数の大都市です。
""" * 60

# 好み比較データ：同じ質問に対する「丁寧(chosen)」「そっけない(rejected)」ペア
preference_pairs = [
    ("日本の首都は?", "東京です。ご質問ありがとうございます。", "東京。"),
    ("今日の天気は?", "申し訳ありませんが、天気情報は分かりかねます。", "知らない。"),
    ("ありがとう", "どういたしまして。お役に立てて嬉しいです。", "はい。"),
] * 40

specials = ["<Q>", "<A>", "<EOS>", "<PAD>"]
raw = pretrain_text + "".join(q + c + r for q, c, r in preference_pairs) + "".join(specials)
chars = sorted(set(raw))
vocab = specials + [c for c in chars if c not in specials]
stoi = {t: i for i, t in enumerate(vocab)}
itos = {i: t for t, i in stoi.items()}
vocab_size = len(vocab)
PAD_ID, EOS_ID = stoi["<PAD>"], stoi["<EOS>"]
print(f"語彙サイズ: {vocab_size}")


def tokenize(s):
    ids, i = [], 0
    while i < len(s):
        matched = False
        for sp in specials:
            if s[i:i + len(sp)] == sp:
                ids.append(stoi[sp]); i += len(sp); matched = True; break
        if not matched:
            ids.append(stoi[s[i]]); i += 1
    return ids


def detok(ids):
    return "".join(itos[i] for i in ids)


block_size = 48
batch_size = 8

# -----------------------------------------------------------------
# 2. モデル定義（Day3/6と同じシンプルなTinyGPT）
# -----------------------------------------------------------------
class Block(nn.Module):
    def __init__(self, d_model, n_heads):
        super().__init__()
        self.n_heads = n_heads
        self.qkv = nn.Linear(d_model, 3 * d_model, bias=False)
        self.proj = nn.Linear(d_model, d_model, bias=False)
        self.ff = nn.Sequential(nn.Linear(d_model, 4 * d_model), nn.GELU(), nn.Linear(4 * d_model, d_model))
        self.ln1, self.ln2 = nn.LayerNorm(d_model), nn.LayerNorm(d_model)
        mask = torch.triu(torch.ones(block_size, block_size), diagonal=1).bool()
        self.register_buffer("mask", mask)

    def forward(self, x):
        B, T, C = x.shape
        h = self.ln1(x)
        qkv = self.qkv(h).view(B, T, 3, self.n_heads, C // self.n_heads)
        q, k, v = [t.transpose(1, 2) for t in qkv.unbind(2)]
        att = (q @ k.transpose(-2, -1)) / math.sqrt(q.size(-1))
        att = att.masked_fill(self.mask[:T, :T], float("-inf"))
        att = F.softmax(att, dim=-1)
        out = (att @ v).transpose(1, 2).contiguous().view(B, T, C)
        x = x + self.proj(out)
        x = x + self.ff(self.ln2(x))
        return x


class TinyGPT(nn.Module):
    def __init__(self, vocab_size, d_model=64, n_heads=4, n_layers=4):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab_size, d_model)
        self.pos_emb = nn.Embedding(block_size, d_model)
        self.blocks = nn.ModuleList([Block(d_model, n_heads) for _ in range(n_layers)])
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size)

    def forward(self, idx):
        B, T = idx.shape
        pos = torch.arange(T, device=idx.device)
        x = self.tok_emb(idx) + self.pos_emb(pos)
        for blk in self.blocks:
            x = blk(x)
        return self.head(self.ln_f(x))

    @torch.no_grad()
    def generate(self, idx, max_new_tokens=20):
        for _ in range(max_new_tokens):
            logits = self(idx[:, -block_size:])
            next_id = torch.argmax(logits[:, -1, :], dim=-1, keepdim=True)
            idx = torch.cat([idx, next_id], dim=1)
            if next_id.item() == EOS_ID:
                break
        return idx


def make_batch(seqs):
    xs, ys, masks = [], [], []
    for ids in seqs:
        ids = ids[:block_size + 1]
        pad_len = block_size + 1 - len(ids)
        ids = ids + [PAD_ID] * pad_len
        xs.append(ids[:-1]); ys.append(ids[1:])
        masks.append([1.0] * (len(ids) - 1 - pad_len) + [0.0] * pad_len)
    return (torch.tensor(xs, device=device), torch.tensor(ys, device=device),
            torch.tensor(masks, device=device))


def seq_logprob(model, x, y, mask):
    """1シーケンス全体の対数尤度 sum_t log pi(y_t | y_<t) をトークンmask付きで計算"""
    logits = model(x)
    logp = F.log_softmax(logits, dim=-1)
    token_logp = torch.gather(logp, 2, y.unsqueeze(-1)).squeeze(-1)
    return (token_logp * mask).sum(dim=1)


# -----------------------------------------------------------------
# 3. ステップ0: 事前学習＋簡単なSFT（Day6相当。DPOの前提となる方策を作る）
# -----------------------------------------------------------------
pretrain_ids = tokenize(pretrain_text)


def get_pretrain_batch():
    seqs = [pretrain_ids[s:s + block_size + 1] for s in
            torch.randint(0, len(pretrain_ids) - block_size - 1, (batch_size,)).tolist()]
    return make_batch(seqs)


model = TinyGPT(vocab_size).to(device)
opt = torch.optim.AdamW(model.parameters(), lr=3e-3)
print("\n=== ステップ0: 事前学習 ===")
for step in range(300):
    x, y, m = get_pretrain_batch()
    logp = seq_logprob(model, x, y, m)
    loss = -(logp / m.sum(dim=1).clamp(min=1)).mean()
    opt.zero_grad(); loss.backward(); opt.step()
    if step % 100 == 0:
        print(f"step {step:4d} | loss {loss.item():.3f}")

# 軽くSFT（chosen側だけで教師あり学習し、質問に答える体裁を整える）
sft_seqs = [tokenize(f"<Q>{q}<A>{c}<EOS>") for q, c, r in preference_pairs]
print("\n=== 軽いSFT（質問応答の体裁を整える） ===")
for step in range(200):
    idxs = torch.randint(0, len(sft_seqs), (batch_size,))
    x, y, m = make_batch([sft_seqs[i] for i in idxs])
    logp = seq_logprob(model, x, y, m)
    loss = -(logp / m.sum(dim=1).clamp(min=1)).mean()
    opt.zero_grad(); loss.backward(); opt.step()
    if step % 100 == 0:
        print(f"step {step:4d} | loss {loss.item():.3f}")


def ask(m, question, max_new=20):
    m.eval()
    prompt = tokenize(f"<Q>{question}<A>")
    out = m.generate(torch.tensor([prompt], device=device), max_new_tokens=max_new)
    m.train()
    return detok(out[0].tolist())


print("\n=== SFT直後（DPO前）の回答 ===")
for q, c, r in preference_pairs[:3]:
    print(f"Q: {q}  →  {ask(model, q)}")

# -----------------------------------------------------------------
# 4. DPO本体
# -----------------------------------------------------------------
ref_model = copy.deepcopy(model).to(device)
for p in ref_model.parameters():
    p.requires_grad = False
ref_model.eval()

beta = 0.5  # DPOの温度パラメータ：大きいほどrefからのズレを許容しない

chosen_seqs = [tokenize(f"<Q>{q}<A>{c}<EOS>") for q, c, r in preference_pairs]
rejected_seqs = [tokenize(f"<Q>{q}<A>{r}<EOS>") for q, c, r in preference_pairs]

opt = torch.optim.AdamW(model.parameters(), lr=1e-3)

print(f"\n=== ステップ1: DPO学習 (beta={beta}) ===")
for step in range(300):
    idxs = torch.randint(0, len(chosen_seqs), (batch_size,))
    xc, yc, mc = make_batch([chosen_seqs[i] for i in idxs])
    xr, yr, mr = make_batch([rejected_seqs[i] for i in idxs])

    logp_c_theta = seq_logprob(model, xc, yc, mc)
    logp_r_theta = seq_logprob(model, xr, yr, mr)
    with torch.no_grad():
        logp_c_ref = seq_logprob(ref_model, xc, yc, mc)
        logp_r_ref = seq_logprob(ref_model, xr, yr, mr)

    # DPO損失: -log sigmoid( beta * [(logp_c_theta - logp_c_ref) - (logp_r_theta - logp_r_ref)] )
    logits = beta * ((logp_c_theta - logp_c_ref) - (logp_r_theta - logp_r_ref))
    loss = -F.logsigmoid(logits).mean()

    opt.zero_grad(); loss.backward(); opt.step()

    if step % 100 == 0:
        with torch.no_grad():
            # chosenがrejectedよりどれだけ選ばれやすくなっているか（正なら好ましい方向）
            margin = (logp_c_theta - logp_r_theta).mean().item()
        print(f"step {step:4d} | DPO loss {loss.item():.3f} | chosen-rejected logp差 {margin:+.3f}")

print("\n=== DPO後の回答（丁寧な回答=chosen側に寄っているはず） ===")
for q, c, r in preference_pairs[:3]:
    print(f"Q: {q}")
    print(f"  chosen候補 : {c}")
    print(f"  rejected候補: {r}")
    print(f"  実際の生成  : {ask(model, q)}")

# -----------------------------------------------------------------
# 5. 定量比較：DPO前後でchosen/rejectedの相対選好がどう変わったか
# -----------------------------------------------------------------
print("\n=== 定量評価: log pi(chosen) - log pi(rejected) の変化 ===")
with torch.no_grad():
    xc, yc, mc = make_batch(chosen_seqs[:len(preference_pairs)])
    xr, yr, mr = make_batch(rejected_seqs[:len(preference_pairs)])
    diff_ref = (seq_logprob(ref_model, xc, yc, mc) - seq_logprob(ref_model, xr, yr, mr)).mean().item()
    diff_now = (seq_logprob(model, xc, yc, mc) - seq_logprob(model, xr, yr, mr)).mean().item()
print(f"DPO前（ref, ≈SFT直後）: {diff_ref:+.3f}")
print(f"DPO後（theta）        : {diff_now:+.3f}")
print("→ 値がより大きくプラスになっていれば、chosen(丁寧な回答)がより選ばれやすくなった証拠")
