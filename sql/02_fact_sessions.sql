-- 02_fact_sessions.sql
-- Session fact table containing the chronological ordering key (visit_id) per user.
-- Grain: One row per session.
-- Applies ROW_NUMBER() over full_visitor_id ordered by visit_id to establish touchpoint sequence.
--
-- Note: No WHERE channel_grouping IS NOT NULL filter is applied here.
-- The raw data has zero NULL channel_grouping values (verified at extraction time),
-- so filtering would be silently misleading if NULLs ever appeared in a future extract.

DROP TABLE IF EXISTS fact_sessions;

CREATE TABLE fact_sessions AS
SELECT 
    full_visitor_id,
    visit_id,
    channel_grouping,
    ROW_NUMBER() OVER (PARTITION BY full_visitor_id ORDER BY visit_id, channel_grouping) AS touchpoint_sequence
FROM staging_sessions;
