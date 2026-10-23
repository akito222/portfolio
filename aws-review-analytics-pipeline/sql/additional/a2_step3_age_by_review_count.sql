-- Additional task 2 / STEP3: ages ordered by NUMBER of reviews (many -> few)
SELECT
  age,
  COUNT(review_id) AS review_count
FROM review_analytics.amazon_reviews
GROUP BY age
ORDER BY review_count DESC;
