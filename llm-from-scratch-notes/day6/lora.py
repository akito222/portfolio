"""
Day6: LoRA 層（テストから import できるよう、day6_sft_lora.py と同じ式を関数・クラスとして切り出した版）
=================================================================
  y = W x + (alpha / r) * B(A(x))
 ・W（元の重み）は凍結し、低ランク行列 A (d_in×r), B (r×d_out) だけを学習する
 ・B をゼロで初期化するので、学習開始時の増分 ΔW は 0（元のモデルと完全に同じ出力から始まる）
 ・学習後は ΔW = (alpha/r)·(A B)^T を W に足し込めば、推論時の追加コストはゼロ
"""

import torch
import torch.nn as nn


class LoRALinear(nn.Module):
    def __init__(self, in_features, out_features, r=4, alpha=8, bias=True):
        super().__init__()
        self.base = nn.Linear(in_features, out_features, bias=bias)
        self.scaling = alpha / r
        self.lora_A = nn.Parameter(torch.randn(in_features, r) * 0.01)
        self.lora_B = nn.Parameter(torch.zeros(r, out_features))
        for p in self.base.parameters():
            p.requires_grad = False

    def forward(self, x):
        return self.base(x) + self.scaling * (x @ self.lora_A @ self.lora_B)

    def delta_weight(self):
        """nn.Linear の重みと同じ形 (out, in) の増分 ΔW。"""
        return self.scaling * (self.lora_A @ self.lora_B).T

    @torch.no_grad()
    def merged_linear(self):
        """ΔW を足し込んだ普通の nn.Linear を返す（推論時はこれだけで済む）。"""
        out = nn.Linear(self.base.in_features, self.base.out_features, bias=self.base.bias is not None)
        out.weight.copy_(self.base.weight + self.delta_weight())
        if self.base.bias is not None:
            out.bias.copy_(self.base.bias)
        return out


def count_trainable(module):
    return sum(p.numel() for p in module.parameters() if p.requires_grad)
