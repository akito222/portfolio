import pytest

from minhash import char_ngrams, deduplicate, estimate_jaccard, jaccard, signature


def test_identical_sets_have_identical_signatures():
    s = char_ngrams("ロボットが唐揚げをつかむ")
    assert estimate_jaccard(signature(s, 64), signature(s, 64)) == 1.0


def test_minhash_estimate_is_close_to_true_jaccard():
    a = set(range(0, 300))
    b = set(range(100, 400))
    est = estimate_jaccard(signature(a, 512), signature(b, 512))
    assert est == pytest.approx(jaccard(a, b), abs=0.08)  # 真値 0.5


def test_deduplicate_removes_near_duplicates_only():
    docs = ["ロボットが弁当箱に唐揚げを盛り付ける。",
            "ロボットが弁当箱に唐揚げを盛り付ける！",
            "強化学習で双腕の協調動作を学習する。"]
    assert deduplicate(docs, threshold=0.7) == [docs[0], docs[2]]
