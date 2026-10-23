import numpy as np
import pytest

from sampling import (greedy, sample, self_consistency, self_consistency_accuracy, softmax,
                      top_k_filter, top_p_filter)

LOGITS = np.array([2.0, 1.0, 0.5, -1.0])


@pytest.mark.parametrize("t", [0.1, 1.0, 5.0])
def test_softmax_sums_to_one(t):
    assert softmax(LOGITS, t).sum() == pytest.approx(1.0)


def test_softmax_is_stable_for_huge_logits():
    p = softmax(np.array([1000.0, 999.0]))
    assert np.all(np.isfinite(p)) and p.sum() == pytest.approx(1.0)


def test_low_temperature_approaches_greedy():
    assert softmax(LOGITS, 0.01)[greedy(LOGITS)] > 0.999


def test_high_temperature_approaches_uniform():
    assert np.allclose(softmax(LOGITS, 1e4), 0.25, atol=1e-3)


def test_top_k_keeps_exactly_k_highest():
    p = top_k_filter(softmax(LOGITS), 2)
    assert np.count_nonzero(p) == 2 and p[0] > 0 and p[1] > 0
    assert p.sum() == pytest.approx(1.0)


def test_top_p_keeps_smallest_set_reaching_p():
    probs = np.array([0.5, 0.3, 0.15, 0.05])
    assert np.count_nonzero(top_p_filter(probs, 0.5)) == 1
    assert np.count_nonzero(top_p_filter(probs, 0.8)) == 2
    assert np.count_nonzero(top_p_filter(probs, 0.81)) == 3
    assert np.count_nonzero(top_p_filter(probs, 1.0)) == 4


def test_sample_never_picks_filtered_tokens():
    rng = np.random.default_rng(0)
    draws = {sample(LOGITS, temperature=3.0, top_k=2, rng=rng) for _ in range(500)}
    assert draws <= {0, 1}


def test_self_consistency_majority_and_tie_break():
    assert self_consistency(["a", "b", "b", "c"]) == "b"
    assert self_consistency(["x", "y"]) == "x"


def test_majority_vote_helps_when_errors_scatter():
    single = self_consistency_accuracy(0.4, 1, n_wrong=4, trials=1000)
    voted = self_consistency_accuracy(0.4, 15, n_wrong=4, trials=1000)
    assert voted > single + 0.2
