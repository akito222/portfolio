"""
Day7: DPO 損失と GRPO 系のアドバンテージ（テストから import できるよう関数として切り出した版）
=================================================================
DPO（Rafailov+ 2023）:
  L = -log σ( β [ (log π(y_w|x) - log π_ref(y_w|x)) - (log π(y_l|x) - log π_ref(y_l|x)) ] )
  好ましい回答 y_w の「参照モデルからの上がり幅」が、好ましくない回答 y_l より大きいほど損失が小さい。

GRPO（Shao+ 2024）: 同じ質問への G 個の回答の報酬をグループ内で標準化して baseline にする
  A_i = (r_i - mean(r)) / std(r)          → 価値モデル（Critic）が不要
Dr. GRPO（Liu+ 2025）: std で割ると、全員ほぼ同じ報酬の「簡単すぎ / 難しすぎ」の質問で
  小さな差が拡大される偏りがあるとして、std での正規化を外す
  A_i = r_i - mean(r)
"""

import torch
import torch.nn.functional as F


def dpo_loss(logp_chosen, logp_rejected, ref_logp_chosen, ref_logp_rejected, beta=0.1):
    """各引数は系列全体の対数確率（バッチ）。平均損失と、chosen / rejected の暗黙報酬を返す。"""
    reward_chosen = beta * (logp_chosen - ref_logp_chosen)
    reward_rejected = beta * (logp_rejected - ref_logp_rejected)
    loss = -F.logsigmoid(reward_chosen - reward_rejected).mean()
    return loss, reward_chosen.detach(), reward_rejected.detach()


def grpo_advantages(rewards, eps=1e-8):
    """rewards: (G,) または (質問数, G)。最後の軸がグループ。"""
    rewards = torch.as_tensor(rewards, dtype=torch.float32)
    mean = rewards.mean(dim=-1, keepdim=True)
    std = rewards.std(dim=-1, keepdim=True)
    return (rewards - mean) / (std + eps)


def dr_grpo_advantages(rewards):
    rewards = torch.as_tensor(rewards, dtype=torch.float32)
    return rewards - rewards.mean(dim=-1, keepdim=True)
