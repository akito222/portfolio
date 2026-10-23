-- Additional task 3 / STEP2: only the amazon_reviews table.
-- Filtering on table_schema too avoids scanning metadata of every database
-- (information_schema queries over many databases are slow in Athena).
SELECT
  table_schema,
  table_name,
  table_type
FROM information_schema.tables
WHERE table_schema = 'review_analytics'
  AND table_name = 'amazon_reviews';
