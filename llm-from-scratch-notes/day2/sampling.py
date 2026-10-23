"""
Day2: デコーディング（次トークンの選び方）と Self-Consistency を自前実装
=================================================================
LLM が出力するのは「次のトークンの確率分布」だけで、
その分布から実際にどのトークンを選ぶかは別の設計（デコーディング）になる。

このファイルは NumPy だけで以下を実装する（ライブラリの generate() は使わない）:
 ・softmax（温度つき）
 ・Greedy / Top-k / Top-p（nucleus）/ Temperature サンプリング
 ・Self-Consistency（複数回答の多数決）

実験とグラフ生成は day2/experiment.py、テストは tests/test_day2_sampling.py。
"""

from collections import Counter

import numpy as np


def softmax(logits, temperature=1.0):
    """温度つき softmax。temperature が小さいほど分布が尖り、大きいほど平らになる。

    数値安定化のため最大値を引いてから exp を取る（結果は変わらない）。
    """
    if temperature <= 0:
        raise ValueError("temperature は正の値にする（0 に近づけた極限が greedy）")
    z = np.asarray(logits, dtype=np.float64) / temperature
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


def greedy(logits):
    """最も確率の高いトークンを常に選ぶ（決定的）。"""
    return int(np.argmax(logits))


def top_k_filter(probs, k):
    """確率の高い上位 k 個だけ残して再正規化する。"""
    probs = np.asarray(probs, dtype=np.float64)
    if not 1 <= k <= probs.size:
        raise ValueError(f"k は 1〜{probs.size} の範囲にする")
    keep = np.argsort(probs)[::-1][:k]
    out = np.zeros_like(probs)
    out[keep] = probs[keep]
    return out / out.sum()


def top_p_filter(probs, p):
    """確率の高い順に足していき、累積確率が初めて p 以上になるまでの最小集合だけ残す。

    Top-k と違い、残る候補の数が分布の形に応じて変わるのがポイント:
    自信がある場面（尖った分布）では候補が少なく、迷う場面（平らな分布）では多くなる。
    """
    probs = np.asarray(probs, dtype=np.float64)
    if not 0 < p <= 1:
        raise ValueError("p は (0, 1] の範囲にする")
    order = np.argsort(probs)[::-1]
    cum = np.cumsum(probs[order])
    # 累積が p に届いた位置までを含める（先頭の 1 個は必ず残る）
    n_keep = int(np.searchsorted(cum, p - 1e-12) + 1)
    keep = order[:n_keep]
    out = np.zeros_like(probs)
    out[keep] = probs[keep]
    return out / out.sum()


def sample(logits, temperature=1.0, top_k=None, top_p=None, rng=None):
    """温度 → Top-k → Top-p の順に分布を加工してから 1 トークンをサンプリングする。"""
    rng = np.random.default_rng() if rng is None else rng
    probs = softmax(logits, temperature)
    if top_k is not None:
        probs = top_k_filter(probs, top_k)
    if top_p is not None:
        probs = top_p_filter(probs, top_p)
    return int(rng.choice(probs.size, p=probs))


def entropy(probs):
    """分布のエントロピー（nats）。候補がどれだけ散らばっているかの指標。"""
    probs = np.asarray(probs, dtype=np.float64)
    nz = probs[probs > 0]
    return float(-(nz * np.log(nz)).sum())


def self_consistency(answers):
    """複数の回答から最も多い答えを返す（同数のときは先に出た方）。

    CoT で推論経路を何本もサンプリングし、最終回答だけを多数決にかけるのが Self-Consistency。
    「正しい経路は同じ答えに収束しやすく、誤った経路は答えがばらける」ことを利用する。
    """
    if len(answers) == 0:
        raise ValueError("回答が 1 つ以上必要")
    counts = Counter(answers)
    best = max(counts.values())
    for a in answers:
        if counts[a] == best:
            return a


def simulate_solver(rng, p_correct, n_wrong, correct="正解"):
    """1 回の推論を模擬する: 確率 p_correct で正解、それ以外は n_wrong 種類の誤答から一様に選ぶ。

    LLM の代わりにこの簡単なモデルを使い、多数決の効果だけを切り出して調べる。
    """
    if rng.random() < p_correct:
        return correct
    return f"誤答{rng.integers(n_wrong)}"


def self_consistency_accuracy(p_correct, n_samples, n_wrong=4, trials=2000, seed=0):
    """n_samples 本の回答を多数決したときの正解率をモンテカルロで推定する。"""
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(trials):
        answers = [simulate_solver(rng, p_correct, n_wrong) for _ in range(n_samples)]
        hits += self_consistency(answers) == "正解"
    return hits / trials
