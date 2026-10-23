import math

import pytest
import torch

from rl_objectives import dpo_loss, dr_grpo_advantages, grpo_advantages


def test_dpo_loss_is_log2_when_policy_equals_reference():
    lp = torch.tensor([-3.0, -5.0])
    loss, rc, rr = dpo_loss(lp, lp - 1, lp, lp - 1)
    assert loss.item() == pytest.approx(math.log(2))
    assert torch.allclose(rc, torch.zeros(2)) and torch.allclose(rr, torch.zeros(2))


def test_dpo_loss_decreases_when_chosen_goes_up():
    ref_c, ref_r = torch.tensor([-4.0]), torch.tensor([-4.0])
    before, _, _ = dpo_loss(ref_c, ref_r, ref_c, ref_r)
    after, _, _ = dpo_loss(ref_c + 2, ref_r - 2, ref_c, ref_r)
    assert after < before


def test_dpo_gradient_pushes_chosen_up_and_rejected_down():
    lc = torch.tensor([-4.0], requires_grad=True)
    lr = torch.tensor([-4.0], requires_grad=True)
    loss, _, _ = dpo_loss(lc, lr, torch.tensor([-4.0]), torch.tensor([-4.0]))
    loss.backward()
    assert lc.grad.item() < 0 < lr.grad.item()  # 損失を下げる方向 = chosen を上げ、rejected を下げる


def test_grpo_advantages_are_standardized_within_group():
    a = grpo_advantages([2.4, 0.8, 1.9, -1.0])
    assert a.mean().item() == pytest.approx(0.0, abs=1e-6)
    assert a.std().item() == pytest.approx(1.0, abs=1e-4)
    assert a.argmax().item() == 0 and a.argmin().item() == 3


def test_grpo_gives_zero_advantage_when_all_rewards_equal():
    assert torch.allclose(grpo_advantages([1.0, 1.0, 1.0]), torch.zeros(3))


def test_dr_grpo_does_not_amplify_tiny_differences():
    tiny = [1.0, 1.0, 1.0, 1.01]
    assert grpo_advantages(tiny).abs().max() > 1.0        # std で割ると小さな差が拡大される
    assert dr_grpo_advantages(tiny).abs().max() < 0.01    # Dr. GRPO はそのまま


def test_grpo_handles_multiple_groups():
    a = grpo_advantages([[1.0, 0.0], [5.0, 3.0]])
    assert torch.allclose(a.mean(dim=-1), torch.zeros(2), atol=1e-6)
