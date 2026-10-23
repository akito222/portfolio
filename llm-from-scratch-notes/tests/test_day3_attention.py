import torch

import day3_transformer as d3


def test_attention_head_does_not_look_at_the_future():
    torch.manual_seed(0)
    head = d3.SelfAttentionHead(d_model=16, head_size=8)
    x = torch.randn(1, 10, 16)
    x_changed = x.clone()
    x_changed[:, 6:] = torch.randn(1, 4, 16)  # 6 番目以降（未来）だけを書き換える
    out, out_changed = head(x), head(x_changed)
    assert torch.allclose(out[:, :6], out_changed[:, :6])
    assert not torch.allclose(out[:, 6:], out_changed[:, 6:])


def test_tinygpt_logits_shape_and_loss():
    torch.manual_seed(0)
    model = d3.TinyGPT(d3.vocab_size, d_model=32, n_heads=4, n_layers=1)
    idx = torch.randint(d3.vocab_size, (2, 12))
    logits, loss = model(idx, idx)
    assert logits.shape == (2, 12, d3.vocab_size)
    assert loss.item() > 0
