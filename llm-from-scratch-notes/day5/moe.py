"""
Day5: Mixture of Experts（MoE）層を自前実装
=================================================================
FFN を「専門家（expert）」の集まりに置き換え、トークンごとに上位 k 個の expert だけを動かす。
パラメータ数は expert の数に比例して増えるが、1 トークンあたりの計算量は k 個分で済む。

 ・ゲート: g = softmax(x W_g) で各 expert の重みを出す
 ・Top-k ルーティング: 上位 k 個だけ残し、その重みを和が 1 になるよう再正規化
 ・負荷分散損失（Switch Transformer 型）: 特定の expert にトークンが偏るのを防ぐ
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class Expert(nn.Module):
    """1 つの expert = 普通の 2 層 FFN。"""

    def __init__(self, d_model, d_hidden):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d_model, d_hidden), nn.GELU(), nn.Linear(d_hidden, d_model))

    def forward(self, x):
        return self.net(x)


class MoELayer(nn.Module):
    def __init__(self, d_model, d_hidden, n_experts=4, top_k=2):
        super().__init__()
        if not 1 <= top_k <= n_experts:
            raise ValueError("top_k は 1〜n_experts の範囲にする")
        self.n_experts, self.top_k = n_experts, top_k
        self.gate = nn.Linear(d_model, n_experts, bias=False)
        self.experts = nn.ModuleList([Expert(d_model, d_hidden) for _ in range(n_experts)])
        self.last_aux_loss = torch.tensor(0.0)
        self.last_routing = None

    def route(self, x):
        """各トークンの (選ばれた expert の番号, その重み, 全 expert の確率) を返す。"""
        probs = F.softmax(self.gate(x), dim=-1)                 # (N, E)
        topv, topi = probs.topk(self.top_k, dim=-1)            # (N, k)
        weights = topv / topv.sum(dim=-1, keepdim=True)        # 選ばれた k 個で再正規化
        return topi, weights, probs

    def forward(self, x):
        shape = x.shape
        x = x.reshape(-1, shape[-1])                           # (N, d)
        topi, weights, probs = self.route(x)

        out = torch.zeros_like(x)
        for e, expert in enumerate(self.experts):
            # expert e が担当するトークンだけを取り出して計算する（担当外は計算しない）
            token_idx, slot = (topi == e).nonzero(as_tuple=True)
            if token_idx.numel() == 0:
                continue
            out.index_add_(0, token_idx, weights[token_idx, slot, None] * expert(x[token_idx]))

        # 負荷分散損失: E * Σ_e f_e * P_e
        #   f_e = expert e が 1 位に選ばれたトークンの割合、P_e = expert e への平均ゲート確率
        #   完全に均等なら 1、偏るほど大きくなる
        f = F.one_hot(topi[:, 0], self.n_experts).float().mean(dim=0)
        P = probs.mean(dim=0)
        self.last_aux_loss = self.n_experts * (f * P).sum()
        self.last_routing = topi.detach()
        return out.reshape(shape)

    def expert_load(self):
        """直前の forward で各 expert が担当したトークン数（top-k の全スロットを数える）。"""
        if self.last_routing is None:
            raise RuntimeError("先に forward を呼ぶ")
        return torch.bincount(self.last_routing.flatten(), minlength=self.n_experts)


def active_params_per_token(layer):
    """1 トークンの計算に実際に使われるパラメータ数（ゲート + k 個の expert）。"""
    one_expert = sum(p.numel() for p in layer.experts[0].parameters())
    return layer.gate.weight.numel() + layer.top_k * one_expert
