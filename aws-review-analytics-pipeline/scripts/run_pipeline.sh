#!/usr/bin/env bash
# Run the pipeline once by hand (what the hands-on did by clicking in the console).
#   crawl raw -> DataBrew recipe jobs -> crawl curated -> Parquet ETL -> Bedrock -> crawl AI output
set -euo pipefail

PREFIX="${PREFIX:-review-analytics}"
REGION="${AWS_REGION:-ap-northeast-1}"
export AWS_REGION="$REGION"

wait_crawler() {
  local name="$1"
  aws glue start-crawler --name "$name"
  echo -n "crawler $name "
  sleep 10
  while [[ "$(aws glue get-crawler --name "$name" --query Crawler.State --output text)" != "READY" ]]; do
    echo -n "."; sleep 15
  done
  echo " $(aws glue get-crawler --name "$name" --query Crawler.LastCrawl.Status --output text)"
}

wait_databrew() {
  local job="$1" run
  run=$(aws databrew start-job-run --name "$job" --query RunId --output text)
  echo -n "databrew $job "
  while :; do
    state=$(aws databrew describe-job-run --name "$job" --run-id "$run" --query State --output text)
    case "$state" in
      SUCCEEDED) echo " $state"; return 0 ;;
      FAILED|STOPPED|TIMEOUT) echo " $state"; return 1 ;;
    esac
    echo -n "."; sleep 15
  done
}

wait_glue_job() {
  local job="$1" run
  run=$(aws glue start-job-run --job-name "$job" --query JobRunId --output text)
  echo -n "glue job $job "
  while :; do
    state=$(aws glue get-job-run --job-name "$job" --run-id "$run" --query JobRun.JobRunState --output text)
    case "$state" in
      SUCCEEDED) echo " $state"; return 0 ;;
      FAILED|STOPPED|TIMEOUT|ERROR) echo " $state"; return 1 ;;
    esac
    echo -n "."; sleep 20
  done
}

wait_crawler  "${PREFIX}-crawler-raw"
wait_databrew "${PREFIX}-profile"
wait_databrew "${PREFIX}-recipe-reviews"
wait_databrew "${PREFIX}-recipe-reviews-add"
wait_crawler  "${PREFIX}-crawler-databrew"
wait_glue_job "${PREFIX}-etl-parquet"
wait_glue_job "${PREFIX}-bedrock-analysis"
wait_crawler  "${PREFIX}-crawler-ai"

echo "all done. try: python scripts/athena_query.py sql/handson/h3_books_high_rating_parquet.sql"
