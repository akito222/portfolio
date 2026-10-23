-- Additional task 3 / STEP1: database name, table name and table type of every table.
-- Athena exposes the Glue Data Catalog through the ANSI information_schema.
SELECT
  table_schema,   -- = Glue database
  table_name,
  table_type
FROM information_schema.tables;
