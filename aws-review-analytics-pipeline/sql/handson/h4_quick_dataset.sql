-- Hands-on 4: custom SQL used as the Amazon Quick dataset (SPICE import).
-- review_date comes from the raw table, so the JOIN is done here instead of in Quick.
SELECT
  r.review_id,
  r.product_title,
  r.star_rating,
  CAST(r.review_date AS DATE) AS review_date,
  a.ai_sentiment,
  a.ai_summary,
  a.gap_flag,
  CASE
    WHEN (r.star_rating >= 4 AND a.ai_sentiment IN ('Negative', 'Neutral'))
      OR (r.star_rating <= 2 AND a.ai_sentiment IN ('Positive', 'Neutral'))
    THEN 1 ELSE 0
  END AS gap_flag_broad
FROM review_analytics.amazon_reviews AS r
JOIN review_analytics.ai_reviews_output AS a
  ON r.review_id = a.review_id;
