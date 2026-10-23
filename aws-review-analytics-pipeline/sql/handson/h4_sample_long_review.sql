-- Hands-on 4: pick one long, highly rated review to try prompts in the Bedrock playground
SELECT
  review_id,
  star_rating,
  review_body
FROM review_analytics.amazon_reviews
WHERE LENGTH(review_body) > 100
ORDER BY star_rating DESC
LIMIT 1;
