import pytest
import torch

from attention import naive_attention, n_scores, tiled_attention, window_attention
from moe import MoELayer, active_params_per_token
from quantization import (absmax_quantize, dequantize, make_activations, matmul_int8_mixed,
                          matmul_int8_tensorwise, relative_error)


# ---- Attention ----
@pytest.mark.parametrize("causal", [True, False])
@pytest.mark.parametrize("T,block", [(50, 16), (64, 64), (7, 3)])
def test_tiled_attention_matches_naive(T, block, causal):
    torch.manual_seed(0)
    q, k, v = (torch.randn(2, T, 8) for _ in range(3))
    assert torch.allclose(tiled_attention(q, k, v, block, causal), naive_attention(q, k, v, causal), atol=1e-5)


def test_naive_attention_is_causal():
    torch.manual_seed(0)
    q, k, v = (torch.randn(10, 8) for _ in range(3))
    v2 = v.clone()
    v2[5:] += 10.0
    assert torch.allclose(naive_attention(q, k, v)[:5], naive_attention(q, k, v2)[:5])


def test_window_equals_full_when_window_covers_everything():
    torch.manual_seed(0)
    q, k, v = (torch.randn(20, 8) for _ in range(3))
    assert torch.allclose(window_attention(q, k, v, window=20), naive_attention(q, k, v), atol=1e-6)


def test_score_counts():
    assert n_scores(4, "full") == 10            # 1 + 2 + 3 + 4
    assert n_scores(4, "window", window=2) == 7  # 1 + 2 + 2 + 2


# ---- MoE ----
def test_moe_output_shape_and_topk_routing():
    torch.manual_seed(0)
    layer = MoELayer(d_model=8, d_hidden=16, n_experts=4, top_k=2)
    x = torch.randn(3, 5, 8)
    assert layer(x).shape == x.shape
    topi, weights, probs = layer.route(x.reshape(-1, 8))
    assert topi.shape == (15, 2)
    assert torch.allclose(weights.sum(-1), torch.ones(15))
    assert torch.allclose(probs.sum(-1), torch.ones(15))
    assert int(layer.expert_load().sum()) == 15 * 2


def test_moe_with_one_expert_equals_that_expert():
    torch.manual_seed(0)
    layer = MoELayer(d_model=8, d_hidden=16, n_experts=1, top_k=1)
    x = torch.randn(6, 8)
    assert torch.allclose(layer(x), layer.experts[0](x), atol=1e-6)


def test_aux_loss_is_one_when_perfectly_balanced():
    layer = MoELayer(d_model=4, d_hidden=8, n_experts=4, top_k=1)
    with torch.no_grad():
        layer.gate.weight.copy_(torch.eye(4) * 10)
    layer(torch.eye(4))  # トークン i は expert i に送られる
    assert layer.last_aux_loss.item() == pytest.approx(1.0, abs=1e-3)


def test_active_params_do_not_grow_with_experts():
    small = MoELayer(8, 16, n_experts=2, top_k=2)
    big = MoELayer(8, 16, n_experts=16, top_k=2)
    assert active_params_per_token(big) - active_params_per_token(small) == 8 * 14  # 増えるのはゲートだけ


# ---- 量子化 ----
def test_absmax_roundtrip_error_is_within_half_step():
    x = torch.randn(64, 32)
    q, s = absmax_quantize(x)
    assert q.dtype == torch.int8 and int(q.abs().max()) == 127
    assert (dequantize(q, s) - x).abs().max() <= s / 2 + 1e-6


def test_mixed_decomposition_beats_absmax_with_outliers():
    X = make_activations(64, 128, n_outlier_dims=2, seed=0)
    W = torch.randn(128, 32) * 0.05
    Y = X @ W
    assert relative_error(matmul_int8_mixed(X, W), Y) < relative_error(matmul_int8_tensorwise(X, W), Y) / 5
