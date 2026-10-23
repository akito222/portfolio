#!/usr/bin/env bash
# Deploy the 4 stacks in order, upload scripts / data, publish the DataBrew recipe.
#
#   AWS_REGION=ap-northeast-1 ./scripts/deploy.sh
#
# Prerequisites: AWS CLI v2, credentials, Bedrock model access (for the AI job),
# data/amazon_reviews_5.csv and data/amazon_reviews_add.csv (see data/README.md).
set -euo pipefail

PREFIX="${PREFIX:-review-analytics}"
REGION="${AWS_REGION:-ap-northeast-1}"
CFN_DIR="$(cd "$(dirname "$0")/../infra/cloudformation" && pwd)"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

deploy() {
  local name="$1" file="$2"; shift 2
  echo "==> deploying ${PREFIX}-${name}"
  aws cloudformation deploy \
    --region "$REGION" \
    --stack-name "${PREFIX}-${name}" \
    --template-file "${CFN_DIR}/${file}" \
    --capabilities CAPABILITY_NAMED_IAM \
    --no-fail-on-empty-changeset \
    --parameter-overrides Prefix="$PREFIX" "$@"
}

# 1. data lake foundation
deploy datalake 01-datalake.yaml
BUCKET=$(aws cloudformation describe-stacks --region "$REGION" --stack-name "${PREFIX}-datalake" \
  --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text)
echo "bucket: $BUCKET"

# 2. upload job scripts + data (data must exist before DataBrew datasets are used)
aws s3 cp "${ROOT}/glue/jobs/reviews_to_parquet.py" "s3://${BUCKET}/glue-assets/scripts/" --region "$REGION"
aws s3 cp "${ROOT}/bedrock/analyze_reviews.py"      "s3://${BUCKET}/glue-assets/scripts/" --region "$REGION"
aws s3 cp "${ROOT}/data/amazon_reviews_5.csv"   "s3://${BUCKET}/raw/amazon_reviews/"     --region "$REGION"
aws s3 cp "${ROOT}/data/amazon_reviews_add.csv" "s3://${BUCKET}/raw/amazon_reviews_add/" --region "$REGION"

# 3. DataBrew datasets + recipe, then publish the recipe (jobs must pin a published version)
deploy databrew 02-databrew-recipe.yaml
RECIPE="${PREFIX}-reviews-recipe"
VERSION=$(aws databrew list-recipe-versions --region "$REGION" --name "$RECIPE" \
  --query "max_by(Recipes, &RecipeVersion).RecipeVersion" --output text 2>/dev/null || true)
if [[ -z "$VERSION" || "$VERSION" == "None" ]]; then
  aws databrew publish-recipe --region "$REGION" --name "$RECIPE" --description "initial"
  VERSION=$(aws databrew list-recipe-versions --region "$REGION" --name "$RECIPE" \
    --query "max_by(Recipes, &RecipeVersion).RecipeVersion" --output text)
fi
echo "recipe version: $VERSION"

# 4. processing jobs, 5. automation
deploy processing 03-processing.yaml RecipeVersion="$VERSION"
deploy automation 04-automation.yaml

echo "done. next: ./scripts/run_pipeline.sh"
