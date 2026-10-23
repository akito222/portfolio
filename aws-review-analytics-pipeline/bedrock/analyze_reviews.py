"""Batch review analysis with Amazon Bedrock.

For each review: ask the model for a short Japanese summary, a sentiment label and
the reason for any gap between the star rating and the text, then write JSONL to S3
so that a Glue crawler can catalog it and Athena can JOIN it with the raw table.

Runs as
  * a Glue Python shell job (infra/cloudformation/03-processing.yaml), or
  * locally:  python bedrock/analyze_reviews.py --bucket ... --max-records 20

Differences from the notebook used in the hands-on (and why):
  * Converse API instead of invoke_model  -> same code works for Nova / Claude / Llama
  * temperature=0                          -> labels are reproducible between runs
  * adaptive retries                       -> survives ThrottlingException on bursts
  * stratified sampling by star rating     -> the first 100 rows are mostly 5-star
                                              (dataset is ~57% 5-star), so low-star
                                              gaps were barely sampled
  * gap_reason is kept in the output       -> the notebook generated it but dropped it
  * strict AND broad gap flags             -> notebook (strict) and SQL (broad, incl.
                                              Neutral) used different definitions
  * CSV is streamed from S3                -> memory does not grow with file size
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Iterable, Iterator, List, Optional

SENTIMENTS = ("Positive", "Negative", "Neutral")

PROMPT_TEMPLATE = """以下はある商品のレビュー本文です。次の3点をJSON形式のみで出力してください。前置きや説明文は不要です。
1. summary: 30文字程度の日本語要約
2. sentiment: "Positive" "Negative" "Neutral" のいずれか（★の数ではなく本文のトーンで判定）
3. gap_reason: 星評価(star_rating)と本文の内容にギャップがあれば一言で理由を説明。ギャップがなければ空文字

star_rating: {star_rating}
review_body: {review_body}
"""

log = logging.getLogger("analyze_reviews")


# ---------------------------------------------------------------------------
# pure functions (unit-tested in tests/test_analyze_reviews.py)
# ---------------------------------------------------------------------------
def build_prompt(star_rating: int, review_body: str, max_chars: int = 2000) -> str:
    body = (review_body or "").replace("<br />", "\n").strip()[:max_chars]
    return PROMPT_TEMPLATE.format(star_rating=star_rating, review_body=body)


_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def parse_model_output(text: str) -> Dict[str, str]:
    """Extract the JSON object from the model output and normalise it.

    Handles ```json fences, leading prose and invalid sentiment values.
    """
    match = _JSON_OBJECT.search(text or "")
    if not match:
        return {"summary": "", "sentiment": "Unknown", "gap_reason": "parse_error"}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"summary": "", "sentiment": "Unknown", "gap_reason": "parse_error"}

    sentiment = str(data.get("sentiment", "")).strip().capitalize()
    if sentiment not in SENTIMENTS:
        sentiment = "Unknown"
    return {
        "summary": str(data.get("summary", "")).strip(),
        "sentiment": sentiment,
        "gap_reason": str(data.get("gap_reason", "") or "").strip(),
    }


def gap_flags(star_rating: int, sentiment: str) -> Dict[str, bool]:
    """Star rating vs. text tone.

    strict: high star (4-5) but Negative, or low star (1-2) but Positive
    broad : strict, plus Neutral on either end (used in the Athena / Quick queries)
    3 stars is neither high nor low, so it never counts as a gap.
    """
    high, low = star_rating >= 4, star_rating <= 2
    strict = (high and sentiment == "Negative") or (low and sentiment == "Positive")
    broad = strict or ((high or low) and sentiment == "Neutral")
    return {"gap_flag": strict, "gap_flag_broad": broad}


def stratified_sample(
    rows: Iterable[Dict[str, str]], n: int, key: str = "star_rating", seed: int = 42
) -> List[Dict[str, str]]:
    """Reservoir-sample about n/num_groups rows per group in one streaming pass."""
    rng = random.Random(seed)
    groups = ["1", "2", "3", "4", "5"]
    per_group = max(1, n // len(groups))
    reservoirs: Dict[str, List[Dict[str, str]]] = {g: [] for g in groups}
    seen: Dict[str, int] = {g: 0 for g in groups}
    for row in rows:
        g = str(row.get(key, "")).split(".")[0]
        if g not in reservoirs:
            continue
        seen[g] += 1
        res = reservoirs[g]
        if len(res) < per_group:
            res.append(row)
        else:
            j = rng.randrange(seen[g])
            if j < per_group:
                res[j] = row
    out = [r for g in groups for r in reservoirs[g]]
    return out[:n]


def head(rows: Iterable[Dict[str, str]], n: int) -> List[Dict[str, str]]:
    out = []
    for row in rows:
        if len(out) >= n:
            break
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# AWS calls
# ---------------------------------------------------------------------------
class ReviewAnalyzer:
    def __init__(self, bedrock_client: Any, model_id: str, max_tokens: int = 300):
        self.client = bedrock_client
        self.model_id = model_id
        self.max_tokens = max_tokens

    def analyze(self, star_rating: int, review_body: str) -> Dict[str, str]:
        response = self.client.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [{"text": build_prompt(star_rating, review_body)}]}],
            inferenceConfig={"maxTokens": self.max_tokens, "temperature": 0},
        )
        text = response["output"]["message"]["content"][0]["text"]
        return parse_model_output(text)

    def analyze_row(self, row: Dict[str, str]) -> Dict[str, Any]:
        star = int(float(row["star_rating"]))
        try:
            ai = self.analyze(star, row.get("review_body", ""))
        except Exception as exc:  # keep the batch going; record the failure
            log.warning("review %s failed: %s", row.get("review_id"), exc)
            ai = {"summary": "", "sentiment": "Unknown", "gap_reason": f"error: {type(exc).__name__}"}
        return {
            "review_id": row["review_id"],
            "product_id": row.get("product_id", ""),
            "product_title": row.get("product_title", ""),
            "star_rating": star,
            "ai_summary": ai["summary"],
            "ai_sentiment": ai["sentiment"],
            "ai_gap_reason": ai["gap_reason"],
            **gap_flags(star, ai["sentiment"]),
            "model_id": self.model_id,
        }


def read_csv_from_s3(s3_client: Any, bucket: str, key: str) -> Iterator[Dict[str, str]]:
    body = s3_client.get_object(Bucket=bucket, Key=key)["Body"]
    text = io.TextIOWrapper(body, encoding="utf-8", newline="")
    yield from csv.DictReader(text)


def to_jsonl(records: Iterable[Dict[str, Any]]) -> bytes:
    return ("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n").encode("utf-8")


def run(
    s3_client: Any,
    bedrock_client: Any,
    bucket: str,
    input_key: str,
    output_key: str,
    model_id: str,
    max_records: int,
    sample: str = "stratified",
    workers: int = 4,
) -> List[Dict[str, Any]]:
    rows = read_csv_from_s3(s3_client, bucket, input_key)
    picked = stratified_sample(rows, max_records) if sample == "stratified" else head(rows, max_records)
    log.info("analysing %d reviews with %s", len(picked), model_id)

    analyzer = ReviewAnalyzer(bedrock_client, model_id)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(analyzer.analyze_row, picked))

    s3_client.put_object(Bucket=bucket, Key=output_key, Body=to_jsonl(results))
    gaps = sum(r["gap_flag"] for r in results)
    log.info("wrote %d records (strict gaps: %d) -> s3://%s/%s", len(results), gaps, bucket, output_key)
    return results


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bedrock review analysis")
    p.add_argument("--bucket", required=True)
    p.add_argument("--input-key", default="raw/amazon_reviews/amazon_reviews_5.csv")
    p.add_argument("--output-key", default="ai/ai_reviews_output/ai_reviews.jsonl")
    p.add_argument("--model-id", default="amazon.nova-lite-v1:0")
    p.add_argument("--max-records", type=int, default=100)
    p.add_argument("--sample", choices=["stratified", "head"], default="stratified")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--region", default=None)
    # Glue passes extra arguments (--job-bookmark-option, ...): ignore unknown ones
    args, _ = p.parse_known_args(argv)
    return args


def main(argv: Optional[List[str]] = None) -> None:
    import boto3
    from botocore.config import Config

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    args = parse_args(argv)
    cfg = Config(retries={"max_attempts": 10, "mode": "adaptive"}, read_timeout=120)
    session = boto3.Session(region_name=args.region)
    run(
        s3_client=session.client("s3", config=cfg),
        bedrock_client=session.client("bedrock-runtime", config=cfg),
        bucket=args.bucket,
        input_key=args.input_key,
        output_key=args.output_key,
        model_id=args.model_id,
        max_records=args.max_records,
        sample=args.sample,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()
