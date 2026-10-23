"""
Day5: Attention の計算量とメモリを比べるための 3 つの実装
=================================================================
 1. naive_attention   : softmax(Q K^T / √d) V をそのまま計算。T×T のスコア行列を丸ごと持つ
 2. tiled_attention   : FlashAttention と同じ「オンライン softmax」で K/V をブロックごとに処理。
                        出力は naive と一致するが、同時に持つスコアは T×B だけで済む
 3. window_attention  : Sparse Attention の一種。各トークンは直前 w 個だけを見る。
                        専用カーネルなら計算するスコアの数が T² から T·w に減るが、出力は naive と変わる（近似）。
                        ここでは出力を確かめるため、T×T 行列を作ってからマスクしている（速くはならない）

注意: tiled_attention は PyTorch の演算を並べただけなので速くはならない。
FlashAttention が速いのは、この計算を 1 つの GPU カーネルにまとめて
低速な GPU メモリ（HBM）への読み書きを減らすから。ここで確かめるのは「同じ答えを、
T×T 行列を作らずに出せる」という数式上の仕組みのほう。
"""

import math

import torch


def causal_mask(T, device=None):
    """True の位置を見えなくする。i 行目は j > i（未来）を見ない。"""
    return torch.triu(torch.ones(T, T, dtype=torch.bool, device=device), diagonal=1)


def naive_attention(q, k, v, causal=True):
    """q, k, v: (..., T, d)"""
    scores = q @ k.transpose(-2, -1) / math.sqrt(q.shape[-1])
    if causal:
        scores = scores.masked_fill(causal_mask(q.shape[-2], q.device), float("-inf"))
    return torch.softmax(scores, dim=-1) @ v


def tiled_attention(q, k, v, block=64, causal=True):
    """オンライン softmax: 最大値 m と分母 l を更新しながら K/V をブロックごとに足し込む。

    新しいブロックで最大値が m_old → m_new に変わったら、それまでの分子と分母に
    exp(m_old - m_new) を掛けて「同じ基準」にそろえ直す。最後に分子 / 分母で正規化する。
    """
    T, d = q.shape[-2], q.shape[-1]
    scale = 1.0 / math.sqrt(d)
    m = torch.full(q.shape[:-1] + (1,), float("-inf"), dtype=q.dtype)  # 行ごとの最大値
    l = torch.zeros(q.shape[:-1] + (1,), dtype=q.dtype)                # 行ごとの分母
    acc = torch.zeros_like(q)                                          # 行ごとの分子
    rows = torch.arange(T).unsqueeze(-1)
    for s in range(0, T, block):
        kb, vb = k[..., s:s + block, :], v[..., s:s + block, :]
        scores = (q @ kb.transpose(-2, -1)) * scale                    # (..., T, B) だけ持つ
        if causal:
            cols = torch.arange(s, s + kb.shape[-2]).unsqueeze(0)
            scores = scores.masked_fill(cols > rows, float("-inf"))
        m_new = torch.maximum(m, scores.amax(dim=-1, keepdim=True))
        # まだ 1 つも見えていない行（m_new = -inf）で nan が出ないようにする
        m_safe = torch.where(torch.isinf(m_new), torch.zeros_like(m_new), m_new)
        p = torch.exp(scores - m_safe)
        correction = torch.exp(m - m_safe)
        l = l * correction + p.sum(dim=-1, keepdim=True)
        acc = acc * correction + p @ vb
        m = m_new
    return acc / l


def window_attention(q, k, v, window=64):
    """各トークンは自分を含む直前 window 個だけを見る（因果的なスライディングウィンドウ）。"""
    T = q.shape[-2]
    i = torch.arange(T).unsqueeze(-1)
    j = torch.arange(T).unsqueeze(0)
    hidden = (j > i) | (j <= i - window)
    scores = q @ k.transpose(-2, -1) / math.sqrt(q.shape[-1])
    scores = scores.masked_fill(hidden, float("-inf"))
    return torch.softmax(scores, dim=-1) @ v


def n_scores(T, kind, window=64):
    """因果 Attention で実際に計算に使うスコアの数。"""
    if kind == "full":
        return T * (T + 1) // 2
    if kind == "window":
        return sum(min(i + 1, window) for i in range(T))
    raise ValueError(kind)


def peak_score_bytes(T, kind, block=64, bytes_per=4):
    """同時にメモリ上に置くスコア行列の大きさ（1 ヘッド分）。"""
    if kind == "naive":
        return T * T * bytes_per
    if kind == "tiled":
        return T * min(block, T) * bytes_per
    raise ValueError(kind)
