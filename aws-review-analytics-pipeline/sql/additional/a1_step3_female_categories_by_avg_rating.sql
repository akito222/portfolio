-- Additional task 1 / STEP3: categories ordered by women's AVERAGE rating (high -> low)
-- WHERE filters rows BEFORE grouping; AVG is computed per group.
SELECT
  product_category,
  AVG(star_rating) AS avg_rating
FROM review_analytics.amazon_reviews
WHERE gender = 'W'
GROUP BY product_category
ORDER BY avg_rating DESC;
