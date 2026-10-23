-- Additional task 1 / STEP2: one row per category (GROUP BY collapses duplicates)
SELECT
  product_category
FROM review_analytics.amazon_reviews
WHERE gender = 'W'
GROUP BY product_category;
