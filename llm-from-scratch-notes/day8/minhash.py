"""
Day8: MinHash による近似重複検出（テストから import できるよう関数として切り出した版）
=================================================================
定理: ランダムなハッシュ関数 h について  P[min h(A) = min h(B)] = Jaccard(A, B)
  → k 個のハッシュ関数で「最小値が一致した割合」を数えれば Jaccard 係数を推定できる。
  文書ごとに k 個の最小値（シグネチャ）だけを持てばよいので、大量の文書でも比較が軽い。
"""

import hashlib


def char_ngrams(text, n=3):
    return {text[i:i + n] for i in range(len(text) - n + 1)}


def jaccard(a, b):
    return len(a & b) / len(a | b) if (a | b) else 0.0


def _hash(item, seed):
    return int(hashlib.md5(f"{seed}_{item}".encode()).hexdigest(), 16)


def signature(items, k=128):
    """k 個のハッシュ関数それぞれでの最小ハッシュ値。"""
    if not items:
        raise ValueError("空集合のシグネチャは定義しない")
    return [min(_hash(x, seed) for x in items) for seed in range(k)]


def estimate_jaccard(sig_a, sig_b):
    return sum(a == b for a, b in zip(sig_a, sig_b)) / len(sig_a)


def deduplicate(docs, threshold=0.8, k=128, n=3):
    """推定 Jaccard が threshold 以上の文書を、先に出たものだけ残して取り除く。"""
    kept, sigs = [], []
    for doc in docs:
        sig = signature(char_ngrams(doc, n), k)
        if all(estimate_jaccard(sig, s) < threshold for s in sigs):
            kept.append(doc)
            sigs.append(sig)
    return kept
