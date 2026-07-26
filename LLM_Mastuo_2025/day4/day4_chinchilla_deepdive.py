"""
Day4 深掘り: スケール則の完全理解 ― Chinchilla則と計算最適配分
=================================================================
【4つの実験】
 実験1: 計算量の近似式 C ≈ 6ND を確認する
 実験2: IsoFLOP ― 計算予算Cを固定し、NとDの配分を変えて最適点を探す
        （Chinchillaの中心的な実験の再現）
 実験3: Chinchilla則 D≈20N の意味と、GPT-3が「大きすぎた」ことの確認
 実験4: 推論時スケーリング ― 学習だけでなく推論のFLOPsも考えると
        最適なモデルサイズが変わる（Beyond Chinchilla）

※ 本物の学習曲線ではなく、Chinchilla論文のパラメトリックな損失式
   L(N,D) = E + A/N^alpha + B/D^beta を使ってシミュレートする。
   （実際に数十億パラメータを学習するのは不可能なので、
     論文が当てはめた式で「配分の最適化」だけを体感する）

実行: python day4/day4_chinchilla_deepdive.py
"""

import numpy as np

# =================================================================
# Chinchilla論文(Hoffmann+ 2022)がフィットした損失式のパラメータ
# L(N, D) = E + A/N^alpha + B/D^beta
# =================================================================
E = 1.69        # 既約損失（データの本質的なランダムさ。これ以下には下がらない）
A = 406.4
B = 410.7
alpha = 0.34    # モデルサイズの効き
beta = 0.28     # データ量の効き

def loss(N, D):
    """Chinchillaのパラメトリック損失式"""
    return E + A / (N ** alpha) + B / (D ** beta)

def compute_flops(N, D):
    """学習に必要な計算量の近似 C ≈ 6ND"""
    return 6 * N * D


# =================================================================
# 実験1: C ≈ 6ND の確認
# =================================================================
print("="*62)
print("実験1: 計算量の近似式 C ≈ 6ND")
print("="*62)
print("""
パラメータN個のモデルをDトークンで学習する計算量は約 6ND FLOPs。
係数6は「順伝播に2ND + 逆伝播に4ND」の内訳。
GPT-3(N=175B, D=300B tokens)で確認する。
""")
N_gpt3 = 175e9
D_gpt3 = 300e9
C_gpt3 = compute_flops(N_gpt3, D_gpt3)
print(f"GPT-3: N=175B, D=300B トークン")
print(f"  推定計算量 C = 6ND = {C_gpt3:.2e} FLOPs")
print(f"  （講義資料の GPT-3 実測値 3.14e23 FLOPs とほぼ一致）\n")

# =================================================================
# 実験2: IsoFLOP ― 計算予算を固定してN,Dの最適配分を探す
# =================================================================
print("="*62)
print("実験2: IsoFLOP ― 計算予算Cを固定し、最適なN,D配分を探す")
print("="*62)
print("""
計算予算Cを固定すると、C=6ND の制約下で N を決めれば D=C/(6N) が決まる。
Nを小さく(データ多め)〜大きく(データ少なめ)まで振って、
損失が最小になる「ちょうどいい配分」を探す。これがChinchillaの核心実験。
""")

for C in [1e19, 1e21, 1e23]:
    Ns = np.logspace(7, 12, 200)          # モデルサイズを1000万〜1兆で振る
    Ds = C / (6 * Ns)                     # 予算制約から各Nに対応するD
    Ls = loss(Ns, Ds)
    best_i = np.argmin(Ls)
    N_opt, D_opt, L_opt = Ns[best_i], Ds[best_i], Ls[best_i]
    ratio = D_opt / N_opt
    print(f"計算予算 C = {C:.0e} FLOPs")
    print(f"  最適な N = {N_opt:.2e}, D = {D_opt:.2e}, 最小Loss = {L_opt:.4f}")
    print(f"  → D/N 比 = {ratio:.1f} トークン/パラメータ")
    print()

print("→ どの予算でも D/N がおよそ一定のオーダーに落ち着く。")
print("  これがChinchilla則『NとDは同じ割合で増やすべき』の正体。")
print("  ※ 論文の経験則では D/N≈20前後。ここで比が予算ごとに少し動くのは")
print("    使用した損失式で alpha≠beta のため（Nとデータの効きが非対称）。")
print("    重要なのは『NとDを両方バランスよく増やす』という定性的結論。\n")

# =================================================================
# 実験3: Chinchilla則とGPT-3が「大きすぎた」検証
# =================================================================
print("="*62)
print("実験3: GPT-3は本当に『大きすぎた』のか？")
print("="*62)
print("""
GPT-3(N=175B)を、同じ計算予算のままChinchilla最適な配分にし直したら
どうなるか比較する。
""")

C_gpt3 = compute_flops(175e9, 300e9)

# GPT-3の実際の配分での損失
L_gpt3 = loss(175e9, 300e9)

# 同じ予算でChinchilla最適な配分を探す
Ns = np.logspace(9, 12, 500)
Ds = C_gpt3 / (6 * Ns)
Ls = loss(Ns, Ds)
best_i = np.argmin(Ls)
N_opt, D_opt = Ns[best_i], Ds[best_i]
L_opt = Ls[best_i]

print(f"GPT-3の実際の配分:  N=175B, D=300B → Loss={L_gpt3:.4f}, D/N={300/175:.1f}")
print(f"同予算の最適配分:    N={N_opt/1e9:.0f}B, D={D_opt/1e9:.0f}B → Loss={L_opt:.4f}, D/N={D_opt/N_opt:.1f}")
print()
print(f"→ GPT-3はモデルが大きすぎ・データが少なすぎ(D/N={300/175:.1f}しかない)。")
print(f"  同じ計算量でも、もっと小さいモデルを多くのデータで訓練した方が")
print(f"  損失が下がる({L_gpt3:.4f} → {L_opt:.4f})。これがChinchillaの主張。")
print(f"  実際Chinchilla(70B)は より大きいGopher(280B)に勝った。\n")

# =================================================================
# 実験4: 推論時も考慮する（Beyond Chinchilla）
# =================================================================
print("="*62)
print("実験4: 推論コストも考えると最適サイズは変わる（Beyond Chinchilla）")
print("="*62)
print("""
Chinchillaは「学習FLOPs」だけの最適化。だが実運用では推論も繰り返す。
推論を大量に行うなら、小さいモデル(推論が安い)を、Chinchilla最適より
長く学習する方が、トータルコストで得になる（Chinchilla Trapの議論）。
""")

# あるモデルを D_infer 回推論する想定。総FLOPs = 学習6ND + 推論2N*D_infer
def total_flops_with_inference(N, D, n_inference_tokens):
    train = 6 * N * D
    infer = 2 * N * n_inference_tokens  # 推論は順伝播のみ ≈ 2N per token
    return train + infer

target_loss = 2.3  # 到達したい損失レベル

print(f"目標損失 {target_loss} を、推論回数の想定別に最も安く達成する配分:\n")
print(f"{'推論トークン数':>16}{'最適N':>12}{'最適D':>14}{'D/N':>8}")
for n_infer in [0, 1e11, 1e13, 1e15]:
    best = None
    for N in np.logspace(8, 11, 300):
        # この目標損失に到達するのに必要なD（損失式を逆算）
        need = target_loss - E - A / (N ** alpha)
        if need <= 0:
            continue  # このNだけでは目標未達（データ無限でも届かない）
        D = (B / need) ** (1 / beta)
        total = total_flops_with_inference(N, D, n_infer)
        if best is None or total < best[0]:
            best = (total, N, D)
    if best:
        _, N_b, D_b = best
        label = "学習のみ(Chinchilla)" if n_infer == 0 else ""
        print(f"{n_infer:>16.0e}{N_b:>12.2e}{D_b:>14.2e}{D_b/N_b:>8.0f}  {label}")

print()
print("→ 推論トークン数が増えるほど、最適な N は小さく・D は大きくなる。")
print("  つまり『たくさん推論するなら、小さいモデルを長く学習』が正解。")
print("  これがLlama等が『Chinchilla最適より小さく・長く』学習する理由。")
