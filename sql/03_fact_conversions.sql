-- 03_fact_conversions.sql
-- Conversions fact table isolating sessions with completed transactions.
-- Grain: One row per converting session.
-- Filters sessions where transactions >= 1.

DROP TABLE IF EXISTS fact_conversions;

CREATE TABLE fact_conversions AS
SELECT 
    full_visitor_id,
    visit_id,
    transactions,
    revenue
FROM staging_sessions
WHERE transactions >= 1;
