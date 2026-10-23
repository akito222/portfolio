import torch

from lora import LoRALinear, count_trainable


def test_zero_init_keeps_base_output():
    torch.manual_seed(0)
    layer = LoRALinear(16, 8, r=4)
    x = torch.randn(5, 16)
    assert torch.allclose(layer(x), layer.base(x))


def test_only_lora_parameters_are_trainable():
    layer = LoRALinear(64, 32, r=4)
    assert count_trainable(layer) == 64 * 4 + 4 * 32


def test_merged_linear_gives_same_output():
    torch.manual_seed(0)
    layer = LoRALinear(16, 8, r=4)
    with torch.no_grad():
        layer.lora_B.normal_()  # 学習が進んだ状態を模擬
    x = torch.randn(5, 16)
    assert torch.allclose(layer.merged_linear()(x), layer(x), atol=1e-5)
