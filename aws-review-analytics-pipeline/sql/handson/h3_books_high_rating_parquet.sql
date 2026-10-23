-- Hands-on 3 (after): same query on the Parquet table written by the Glue ETL job.
-- product_category is a partition key -> only .../product_category=Books/ is read,
-- and only the product_title / star_rating column chunks inside those files.
SELECT
  product_title,
  AVG(star_rating) AS avg_rate
FROM review_analytics.reviews_parquet
WHERE product_category = 'Books'
GROUP BY product_title
HAVING AVG(star_rating) >= 4.5
ORDER BY avg_rate ASC, product_title ASC;
