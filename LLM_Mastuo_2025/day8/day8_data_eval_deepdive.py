"""
Day8 深掘り: データ整備と評価の数理を完全理解する
=================================================================
【4つの実験】
 実験1: MinHashの原理を実験で証明する
        「最小ハッシュの一致確率 = Jaccard係数」をモンテカルロで確認
 実験2: 講義スライドの例（"I have a pen" vs "I have an orange"）を再現
 実験3: n-gram overlap によるデータ汚染の検出（実務手法）
 実験4: 評価指標の使い分け ― Perplexityが測れないものを理解する

実行: python day8/day8_data_eval_deepdive.py
"""

import hashlib
import random
import statistics

random.seed(8)


# =================================================================
# 共通関数
# =================================================================
def word_ngrams(text, n=1):
    words = text.split()
    if n == 1:
        return set(words)
    return set(tuple(words[i:i+n]) for i in range(len(words)-n+1))


def char_ngrams(text, n=3):
    return set(text[i:i+n] for i in range(len(text)-n+1))


def jaccard(a, b):
    return len(a & b) / len(a | b) if (a | b) else 0.0


def hash_with_seed(item, seed):
    return int(hashlib.md5(f"{seed}_{item}".encode()).hexdigest(), 16)


def minhash_min(s, seed):
    """集合sの、seed番目のハッシュ関数での最小ハッシュ値"""
    return min(hash_with_seed(x, seed) for x in s) if s else 0


# =================================================================
# 実験1: 「最小ハッシュの一致確率 = Jaccard係数」を実験で証明
# =================================================================
print("="*62)
print("実験1: MinHashの原理をモンテカルロで証明")
print("="*62)
print("""
定理: P[min h(A) = min h(B)] = Jaccard(A,B)
これを、たくさんのランダムなハッシュ関数で試して確率を実測し、
理論値（正確なJaccard）と一致するか確かめる。
""")

# 適当な2集合を作る
universe = list(range(50))
A = set(random.sample(universe, 30))
B = set(random.sample(universe, 30))
true_j = jaccard(A, B)

# 10000個のハッシュ関数で「最小値が一致する割合」を実測
num_trials = 10000
matches = sum(1 for seed in range(num_trials)
              if minhash_min(A, seed) == minhash_min(B, seed))
estimated_j = matches / num_trials

print(f"正確なJaccard係数           : {true_j:.4f}")
print(f"MinHash一致率（{num_trials}回試行）: {estimated_j:.4f}")
print(f"誤差                        : {abs(true_j - estimated_j):.4f}")
print("→ 最小ハッシュの一致確率が、確かにJaccard係数に収束している")
print("  【なぜ？】和集合A∪Bの中で最小になる要素はどれも等確率。")
print("  その最小要素がA∩B（共通部分）に入る確率がまさに|A∩B|/|A∪B|＝Jaccard\n")

# ハッシュ関数の個数を増やすと推定が安定することも確認
print("ハッシュ関数の個数 k を変えたときの推定精度:")
for k in [1, 10, 100, 1000]:
    ests = []
    for _ in range(20):  # 20回繰り返してばらつきを見る
        seeds = random.sample(range(100000), k)
        m = sum(1 for s in seeds if minhash_min(A, s) == minhash_min(B, s)) / k
        ests.append(m)
    spread = max(ests) - min(ests)
    print(f"  k={k:4d} | 推定の平均 {statistics.mean(ests):.3f} | ばらつき幅 {spread:.3f}")
print("→ kを増やすほど推定が安定（ばらつきが小さくなる）\n")

# =================================================================
# 実験2: 講義スライドの例を再現
# =================================================================
print("="*62)
print("実験2: 講義スライドの例を再現")
print("="*62)
sent_a = "I have a pen"
sent_b = "I have an orange"
set_a = word_ngrams(sent_a, 1)
set_b = word_ngrams(sent_b, 1)
print(f'A文章: "{sent_a}" → {set_a}')
print(f'B文章: "{sent_b}" → {set_b}')
print(f"共通部分 A∩B = {set_a & set_b}")
print(f"和集合   A∪B = {set_a | set_b}")
print(f"Jaccard = |A∩B|/|A∪B| = {len(set_a & set_b)}/{len(set_a | set_b)} = {jaccard(set_a, set_b):.3f}")
print("→ 講義スライドの通り 2/6 = 1/3 ≈ 0.333\n")

# =================================================================
# 実験3: n-gram overlap によるデータ汚染の検出（実務手法）
# =================================================================
print("="*62)
print("実験3: n-gram overlap によるデータ汚染の検出")
print("="*62)
print("""
実務では、ベンチマーク問題と学習データの間で長いn-gramが一致するかを調べ、
汚染（テスト問題の混入）を検出する。GPT-3やLlamaの論文でも使われた手法。
""")

# ベンチマーク問題
benchmark = "フランスの首都はパリであり ヨーロッパを代表する都市である"

# 学習データ（3つの文書。doc2にベンチマークが紛れ込んでいる=汚染）
train_docs = {
    "doc1": "日本の首都は東京です 人口は非常に多いです",
    "doc2": "フランスの首都はパリであり ヨーロッパを代表する都市である とても美しい",  # 汚染！
    "doc3": "機械学習は面白い分野です 日々研究が進んでいます",
}

def ngram_overlap_score(text_a, text_b, n=5):
    """2つのテキストの重複率（テスト側基準）。
    日本語は単語区切りが曖昧なので、文字n-gram（連続するn文字）で判定する。
    スペースは除去してから文字を連続とみなす。"""
    ta = text_a.replace(" ", "")
    tb = text_b.replace(" ", "")
    ga = char_ngrams(ta, n)
    gb = char_ngrams(tb, n)
    if not ga:
        return 0.0
    return len(ga & gb) / len(ga)

print(f"ベンチマーク問題: 「{benchmark}」\n")
print("各学習文書との 文字5-gram 重複率:")
threshold = 0.3
for name, doc in train_docs.items():
    score = ngram_overlap_score(benchmark, doc, n=5)
    flag = "  ⚠️ 汚染の疑い！" if score >= threshold else "  (クリーン)"
    print(f"  {name}: 重複率 {score:.2f}{flag}")
print(f"\n→ しきい値{threshold}を超えたdoc2を汚染として検出。")
print("  この文書を学習データから除外すれば、公正な評価が保てる。\n")

# =================================================================
# 実験4: 評価指標の使い分け ― Perplexityの限界
# =================================================================
print("="*62)
print("実験4: 評価指標の使い分け ― Perplexityが測れないもの")
print("="*62)
print("""
Perplexityは「次の単語を当てる能力」を測るが、それだけでは不十分。
下記のように、測りたい能力ごとに適切なベンチマークが異なる。
""")

eval_table = [
    ("Perplexity",  "次の単語予測の確信度", "言語モデルとしての基礎性能", "推論・指示追従は測れない"),
    ("MMLU",        "4択知識問題の正答率",   "幅広い知識",              "知識のみ、生成能力は測れない"),
    ("HumanEval",   "コード生成の実行成功率", "プログラミング能力",        "コード特化"),
    ("GSM8K",       "小学校算数の正答率",     "多段階の数値推論",         "数学特化"),
    ("LLM-as-Judge","強いLLMによる採点",     "生成文の総合品質",         "審判モデルのバイアスを継承"),
]
print(f"{'指標':14s}{'測り方':22s}{'測れる能力':20s}{'限界':s}")
print("-"*90)
for name, how, can, cannot in eval_table:
    print(f"{name:14s}{how:22s}{can:20s}{cannot}")

print("""
→ 完全理解のポイント:
  「単一の指標で全能力は測れない」。だから実際のLLM評価は
  複数ベンチマークの組み合わせで多角的に行う。
  そして全ての指標に共通する大前提が『データ汚染の排除』
  （実験3）― これが崩れると、どんな指標も信頼できなくなる。
""")
