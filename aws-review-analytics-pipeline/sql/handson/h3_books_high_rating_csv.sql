-- Hands-on 3 (before): Books with average rating >= 4.5, on the raw CSV table.
-- CSV is row-oriented and unpartitioned -> Athena must scan the WHOLE file
-- even though only 3 columns and 1 category are needed.
SELECT
  product_title,
  AVG(star_rating) AS avg_rate
FROM review_analytics.amazon_reviews
WHERE product_category = 'Books'
GROUP BY product_title
HAVING AVG(star_rating) >= 4.5
ORDER BY avg_rate ASC, product_title ASC;
