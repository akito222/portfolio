#!/usr/bin/env bash
# Tear everything down (reverse order). The bucket is emptied first, otherwise
# CloudFormation cannot delete it. Glue tables created by crawlers / ETL are
# removed together with the database.
set -euo pipefail

PREFIX="${PREFIX:-review-analytics}"
REGION="${AWS_REGION:-ap-northeast-1}"

BUCKET=$(aws cloudformation describe-stacks --region "$REGION" --stack-name "${PREFIX}-datalake" \
  --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text 2>/dev/null || true)

for s in automation processing databrew; do
  echo "==> deleting ${PREFIX}-${s}"
  aws cloudformation delete-stack --region "$REGION" --stack-name "${PREFIX}-${s}"
  aws cloudformation wait stack-delete-complete --region "$REGION" --stack-name "${PREFIX}-${s}"
done

if [[ -n "$BUCKET" && "$BUCKET" != "None" ]]; then
  echo "==> emptying s3://${BUCKET}"
  aws s3 rm "s3://${BUCKET}" --recursive --region "$REGION"
fi
aws cloudformation delete-stack --region "$REGION" --stack-name "${PREFIX}-datalake"
aws cloudformation wait stack-delete-complete --region "$REGION" --stack-name "${PREFIX}-datalake"
echo "deleted."
