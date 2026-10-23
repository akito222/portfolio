-- Hands-on 4: reviews whose text tone does not match the stars ("gap").
-- high stars (4-5) but Negative/Neutral text, or low stars (1-2) but Positive/Neutral text
SELECT
  r.product_title,
  r.star_rating,
  a.ai_sentiment,
  a.ai_summary,
  a.ai_gap_reason
FROM review_analytics.amazon_reviews AS r
JOIN review_analytics.ai_reviews_output AS a
  ON r.review_id = a.review_id
WHERE (r.star_rating >= 4 AND a.ai_sentiment IN ('Negative', 'Neutral'))
   OR (r.star_rating <= 2 AND a.ai_sentiment IN ('Positive', 'Neutral'))
ORDER BY r.star_rating DESC;
