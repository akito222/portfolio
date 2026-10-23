-- Hands-on 1: customers with the most reviews (top 10)
-- COUNT(review_id) per customer_id, sorted descending, LIMIT 10
SELECT
  customer_id,
  COUNT(review_id) AS count_review
FROM review_analytics.amazon_reviews
GROUP BY customer_id
ORDER BY count_review DESC
LIMIT 10;
