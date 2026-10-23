-- Hands-on 4: distribution of star rating x AI sentiment (JOIN raw table with AI output)
SELECT
  r.star_rating,
  a.ai_sentiment,
  COUNT(*) AS cnt
FROM review_analytics.amazon_reviews AS r
JOIN review_analytics.ai_reviews_output AS a
  ON r.review_id = a.review_id
GROUP BY r.star_rating, a.ai_sentiment
ORDER BY r.star_rating DESC, a.ai_sentiment;
