"""
Day5: int8 量子化と、外れ値（outlier）を分けて扱う LLM.int8() 型の行列積を自前実装
=================================================================
absmax 量子化: scale = max|x| / 127,  q = round(x / scale) ∈ [-127, 127]
  → 1 つでも極端に大きい値があると scale が大きくなり、残りの普通の値が粗く丸められる。

大きな LLM では特定の特徴次元にだけ巨大な値（外れ値）が現れることが知られている。
LLM.int8()（Dettmers+ 2022）は、その次元だけを高精度のまま計算し、残りを int8 で計算して足し合わせる。

ここでは 3 つの方式で Y = X W を計算し、誤差を比べる:
 1. per-tensor absmax     : X 全体・W 全体でそれぞれ scale を 1 つ
 2. vector-wise absmax    : X は行ごと、W は列ごとに scale を持つ
 3. mixed (LLM.int8() 型) : 外れ値を含む特徴次元だけ浮動小数点、残りは vector-wise int8
"""

import torch


def absmax_quantize(x, dim=None):
    """absmax で int8 に量子化する。dim を指定するとその軸ごとに scale を持つ。"""
    if dim is None:
        amax = x.abs().max()
    else:
        amax = x.abs().amax(dim=dim, keepdim=True)
    scale = amax.clamp(min=1e-12) / 127.0
    q = torch.round(x / scale).clamp(-127, 127).to(torch.int8)
    return q, scale


def dequantize(q, scale):
    return q.to(torch.float32) * scale


def _int_matmul(qa, qb):
    """int8 同士の積を整数のまま足し上げる（実機の int32 アキュムレータ相当）。

    float64 で計算しても、この規模なら整数の積和は誤差なく表せる。
    """
    return qa.to(torch.float64) @ qb.to(torch.float64)


def matmul_int8_tensorwise(X, W):
    qx, sx = absmax_quantize(X)
    qw, sw = absmax_quantize(W)
    return (_int_matmul(qx, qw) * (sx * sw)).to(torch.float32)


def matmul_int8_vectorwise(X, W):
    qx, sx = absmax_quantize(X, dim=1)   # 行ごと (n, 1)
    qw, sw = absmax_quantize(W, dim=0)   # 列ごと (1, m)
    return (_int_matmul(qx, qw) * (sx * sw)).to(torch.float32)


def outlier_dims(X, threshold=6.0):
    """どこか 1 か所でも |x| が threshold を超える特徴次元（列）を外れ値次元とする。"""
    return (X.abs() > threshold).any(dim=0)


def matmul_int8_mixed(X, W, threshold=6.0):
    """LLM.int8() 型: 外れ値次元は浮動小数点のまま、残りは vector-wise int8 で計算して足す。"""
    mask = outlier_dims(X, threshold)
    y = torch.zeros(X.shape[0], W.shape[1], dtype=torch.float32)
    if mask.any():
        y = y + X[:, mask] @ W[mask, :]
    if (~mask).any():
        y = y + matmul_int8_vectorwise(X[:, ~mask], W[~mask, :])
    return y


def relative_error(y_hat, y):
    return float((y_hat - y).norm() / y.norm())


def make_activations(n, d, n_outlier_dims=0, outlier_scale=60.0, seed=0):
    """普通は N(0,1) の活性化に、指定数の特徴次元だけ巨大な値を混ぜたデータを作る。"""
    g = torch.Generator().manual_seed(seed)
    X = torch.randn(n, d, generator=g)
    if n_outlier_dims:
        dims = torch.randperm(d, generator=g)[:n_outlier_dims]
        X[:, dims] *= outlier_scale
    return X
