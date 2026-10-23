-- Additional task 1 / extra: the plain ranking is dominated by tiny categories
-- (1-10 reviews -> average of 5.0 by chance). Show the sample size and keep only
-- categories with enough reviews. HAVING filters AFTER grouping.
SELECT
  product_category,
  ROUND(AVG(star_rating), 3) AS avg_rating,
  COUNT(*)                   AS review_count
FROM review_analytics.amazon_reviews
WHERE gender = 'W'
GROUP BY product_category
HAVING COUNT(*) >= 100
ORDER BY avg_rating DESC, review_count DESC;
