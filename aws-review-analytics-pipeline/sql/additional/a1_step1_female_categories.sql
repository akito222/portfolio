-- Additional task 1 / STEP1: product_category of reviews written by women
-- gender: 'W' = women, 'M' = men
SELECT
  product_category
FROM review_analytics.amazon_reviews
WHERE gender = 'W';
