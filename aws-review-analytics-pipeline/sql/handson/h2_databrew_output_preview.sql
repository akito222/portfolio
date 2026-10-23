-- Hands-on 2: check the DataBrew recipe-job output (Parquet) after crawling.
-- New columns: product_title_lower, category_star_rating_mean,
--              product_star_rating_mean, verified_purchase_Yes / _No
SELECT
  product_category,
  product_title_lower,
  star_rating,
  category_star_rating_mean,
  product_star_rating_mean,
  verified_purchase_yes,
  verified_purchase_no
FROM review_analytics.databrew_reviews
LIMIT 10;
