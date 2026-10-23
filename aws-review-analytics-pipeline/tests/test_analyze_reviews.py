import io
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bedrock"))

import analyze_reviews as ar  # noqa: E402


@pytest.mark.parametrize(
    "text, expected",
    [
        ('{"summary":"良い","sentiment":"Positive","gap_reason":""}', ("良い", "Positive", "")),
        ('```json\n{"summary":"s","sentiment":"negative","gap_reason":"r"}\n```', ("s", "Negative", "r")),
        ('結果です: {"summary":"s","sentiment":"Neutral","gap_reason":null}', ("s", "Neutral", "")),
        ('{"summary":"s","sentiment":"Mixed","gap_reason":""}', ("s", "Unknown", "")),
        ("JSONではない応答", ("", "Unknown", "parse_error")),
        ('{"summary": "broken"', ("", "Unknown", "parse_error")),
    ],
)
def test_parse_model_output(text, expected):
    out = ar.parse_model_output(text)
    assert (out["summary"], out["sentiment"], out["gap_reason"]) == expected


@pytest.mark.parametrize(
    "star, sentiment, strict, broad",
    [
        (5, "Positive", False, False),
        (5, "Negative", True, True),  # high stars, negative text
        (4, "Neutral", False, True),
        (1, "Positive", True, True),  # low stars, positive text
        (2, "Neutral", False, True),
        (1, "Negative", False, False),
        (3, "Negative", False, False),  # 3 is neither high nor low
        (3, "Neutral", False, False),
    ],
)
def test_gap_flags(star, sentiment, strict, broad):
    assert ar.gap_flags(star, sentiment) == {"gap_flag": strict, "gap_flag_broad": broad}


def test_stratified_sample_covers_every_rating():
    # 90% five-star, like the real data skew
    rows = [{"star_rating": "5", "id": i} for i in range(900)]
    rows += [{"star_rating": str(s), "id": 1000 + s * 100 + i} for s in (1, 2, 3, 4) for i in range(25)]
    sample = ar.stratified_sample(iter(rows), 50)
    counts = {s: sum(r["star_rating"] == s for r in sample) for s in "12345"}
    assert len(sample) == 50
    assert counts == {s: 10 for s in "12345"}
    assert ar.head(iter(rows), 50) == rows[:50]  # head() would be 100% five-star


def test_build_prompt_truncates_and_cleans():
    prompt = ar.build_prompt(5, "a<br />b" + "x" * 5000, max_chars=10)
    assert "review_body: a\nb" + "x" * 7 + "\n" in prompt  # 10 chars kept
    assert "star_rating: 5" in prompt


class FakeBedrock:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.reply, Exception):
            raise self.reply
        return {"output": {"message": {"content": [{"text": self.reply}]}}}


class FakeS3:
    def __init__(self, csv_text):
        self.csv_text = csv_text
        self.put = {}

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.csv_text.encode("utf-8"))}

    def put_object(self, Bucket, Key, Body):
        self.put[Key] = Body


CSV = (ROOT / "tests/fixtures/amazon_reviews_5.csv").read_text(encoding="utf-8")


def test_run_end_to_end_with_stubs():
    bedrock = FakeBedrock('{"summary":"要約","sentiment":"Negative","gap_reason":"本文は不満"}')
    s3 = FakeS3(CSV)
    results = ar.run(s3, bedrock, "b", "in.csv", "out.jsonl", "model-x", max_records=10, workers=2)

    assert len(results) == 10
    assert bedrock.calls[0]["inferenceConfig"]["temperature"] == 0
    lines = s3.put["out.jsonl"].decode("utf-8").strip().split("\n")
    first = json.loads(lines[0])
    assert set(first) >= {"review_id", "star_rating", "ai_sentiment", "ai_gap_reason", "gap_flag", "gap_flag_broad"}
    for r in map(json.loads, lines):
        assert r["gap_flag"] == (r["star_rating"] >= 4)


def test_model_failure_does_not_stop_batch():
    results = ar.run(FakeS3(CSV), FakeBedrock(RuntimeError("throttled")), "b", "k", "o", "m", 5, "head", 1)
    assert len(results) == 5
    assert all(r["ai_sentiment"] == "Unknown" and r["ai_gap_reason"].startswith("error") for r in results)


def test_parse_args_ignores_glue_extras():
    args = ar.parse_args(["--bucket", "b", "--job-bookmark-option", "job-bookmark-disable", "--max-records", "7"])
    assert args.bucket == "b" and args.max_records == 7
