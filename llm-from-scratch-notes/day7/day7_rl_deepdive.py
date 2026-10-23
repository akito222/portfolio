"""
Day7 深掘り: RLHFの数理を完全理解する
=================================================================
【3つの実験】
 実験1: Bradley-Terryモデルで報酬モデルを学習する（RLHF Step2の再現）
 実験2: DPOの「暗黙の報酬」r = beta*log(pi_theta/pi_ref) が
        本物の選好を再現できることを確認する
 実験3: GRPOのアドバンテージ計算（グループ内標準化でCritic不要）を実装する

数式の対応:
  報酬モデル損失:  L_RM = -log sigmoid(r(x,y_w) - r(x,y_l))       ← Bradley-Terry
  DPOの暗黙報酬:   r(x,y) = beta * log(pi_theta(y|x)/pi_ref(y|x))
  GRPOのA:        A_i = (r_i - mean(r)) / std(r)                 ← グループ内標準化

実行: python day7/day7_rl_deepdive.py
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

torch.manual_seed(7)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}\n")

# =================================================================
# 実験1: Bradley-Terryモデルによる報酬モデルの学習
# =================================================================
print("="*62)
print("実験1: 報酬モデルの学習（Bradley-Terryモデル / RLHF Step2）")
print("="*62)
print("""
人間の選好データ「y_w(勝ち) ≻ y_l(負け)」から報酬モデル r を学習する。
Bradley-Terry: P(y_w ≻ y_l) = sigmoid(r(y_w) - r(y_l))
損失:          L = -log sigmoid(r(y_w) - r(y_l))
""")

# トイ設定：回答を4次元の特徴ベクトルで表す。報酬モデルは特徴→スカラーの線形層。
# 「丁寧さ」「正確さ」「簡潔さ」「無礼さ」の4特徴を持つ回答を想定
feature_names = ["丁寧さ", "正確さ", "簡潔さ", "無礼さ"]
# 人間が本当に好む「真の報酬の重み」（無礼さはマイナス）＝ これを当てさせたい
true_w = torch.tensor([1.5, 2.0, 0.5, -3.0], device=device)

def make_answer():
    return torch.rand(4, device=device)

def true_reward(feat):
    return feat @ true_w

# 選好データを生成：2つの回答のうち真の報酬が高い方をy_wとする
def make_pref_batch(n=64):
    a = torch.stack([make_answer() for _ in range(n)])
    b = torch.stack([make_answer() for _ in range(n)])
    ra, rb = true_reward(a[:, None]).squeeze() if False else (a @ true_w), (b @ true_w)
    # y_w = 報酬が高い方
    win_is_a = ra > rb
    y_w = torch.where(win_is_a[:, None], a, b)
    y_l = torch.where(win_is_a[:, None], b, a)
    return y_w, y_l

# 報酬モデル（学習対象）：4次元→スカラーの線形層
reward_model = nn.Linear(4, 1, bias=False).to(device)
opt = torch.optim.Adam(reward_model.parameters(), lr=0.05)

for step in range(400):
    y_w, y_l = make_pref_batch()
    r_w = reward_model(y_w).squeeze()
    r_l = reward_model(y_l).squeeze()
    loss = -F.logsigmoid(r_w - r_l).mean()   # Bradley-Terryの負の対数尤度
    opt.zero_grad(); loss.backward(); opt.step()

learned_w = reward_model.weight.data.squeeze()
# スケールは任意なので、正規化して真の重みと比較
lw = learned_w / learned_w.norm() * true_w.norm()
print("特徴ごとの重み（真の値 vs 学習した報酬モデル）:")
for i, name in enumerate(feature_names):
    print(f"  {name}: 真 {true_w[i]:+.2f}  /  学習 {lw[i]:+.2f}")
print("→ 選好データ（どっちが好きか）だけから、報酬の構造を復元できた")
print("  特に「無礼さ」がマイナスと学習できている＝人間の好みを捉えた\n")

# =================================================================
# 実験2: DPOの「暗黙の報酬」が選好を再現することを確認
# =================================================================
print("="*62)
print("実験2: DPOの暗黙報酬 r = beta*log(pi_theta/pi_ref) の確認")
print("="*62)
print("""
DPOは報酬モデルを別に作らない。代わりに方策そのものが報酬を表す:
  r(x,y) = beta * log( pi_theta(y|x) / pi_ref(y|x) )
この「暗黙の報酬」で、chosen ≻ rejected が正しく順位づけできるか確認する。
""")

# トイ：3つの回答候補に対する ref と theta の（対数）確率を用意
# theta は chosen を高く、rejected を低くするよう学習したと仮定した値
beta = 0.5
answers = ["丁寧な回答(chosen)", "普通の回答", "無礼な回答(rejected)"]
logp_ref   = torch.tensor([-2.0, -2.0, -2.0], device=device)  # refは横並び
logp_theta = torch.tensor([-1.0, -2.2, -4.5], device=device)  # thetaはchosenを上げた

implicit_reward = beta * (logp_theta - logp_ref)
print("各回答の暗黙報酬 r = beta*(logp_theta - logp_ref):")
for name, r in zip(answers, implicit_reward):
    print(f"  {name:22s}: r = {r:+.3f}")
ranking = torch.argsort(implicit_reward, descending=True)
print(f"→ 暗黙報酬による順位: {' ≻ '.join(answers[i] for i in ranking.tolist())}")
print("  報酬モデルを一切作っていないのに、方策の対数確率比だけで")
print("  『丁寧 ≻ 普通 ≻ 無礼』と正しく順位づけできる = DPOの核心\n")

# =================================================================
# 実験3: GRPOのアドバンテージ計算（Critic不要）
# =================================================================
print("="*62)
print("実験3: GRPO ― グループ内標準化でアドバンテージを算出（Critic不要）")
print("="*62)
print("""
PPOは価値モデル(Critic)で「その状態の期待報酬」を推定してから
アドバンテージA = 報酬 - baseline を計算する（重い）。
GRPOは同じ質問へのG個の回答の報酬を使い、グループ内で標準化する:
  A_i = (r_i - mean(r_1..r_G)) / std(r_1..r_G)
→ 価値モデルを学習せずにbaselineを作れる。
""")

# 1つの質問に対して4つの回答をサンプリングし、報酬モデルで採点したと仮定
question = "日本の首都は?"
group_answers = ["東京です。ご質問ありがとうございます。", "東京。", "東京です。", "分かりません。"]
# 実験1の報酬モデルで採点する想定のスコア（例示値）
group_rewards = torch.tensor([2.4, 0.8, 1.9, -1.0], device=device)

mean_r = group_rewards.mean()
std_r = group_rewards.std()
advantages = (group_rewards - mean_r) / (std_r + 1e-8)

print(f"質問: {question}  （G={len(group_answers)}個の回答をサンプリング）")
print(f"{'回答':40s}{'報酬':>8}{'アドバンテージ':>14}")
for ans, r, a in zip(group_answers, group_rewards, advantages):
    sign = "↑良い" if a > 0 else "↓悪い"
    print(f"{ans:38s}{r:>8.2f}{a:>14.3f}  {sign}")
print(f"\nグループ平均報酬(baseline) = {mean_r:.3f}")
print("→ 平均より上の回答は正のアドバンテージ（強化される）、")
print("  下の回答は負（抑制される）。価値モデルなしでbaselineを実現。")
print("  これがGRPOがPPOより軽量な理由。DeepSeek-R1等で採用された。")

# GRPOの方策更新の方向を模式的に示す
print("\n【方策更新のイメージ】")
for ans, a in zip(group_answers, advantages):
    direction = "生成確率を上げる" if a > 0 else "生成確率を下げる"
    print(f"  「{ans[:12]}...」 A={a:+.2f} → {direction}")
