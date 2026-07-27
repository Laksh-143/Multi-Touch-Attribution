-- 05_journey_paths.sql
-- Aggregates scoped session touchpoints into ordered journey path strings per visitor.
-- Feeds downstream heuristic attribution models and exact Shapley coalition enumeration.
--
-- SQLite Compatibility Note:
-- SQLite's GROUP_CONCAT does not support an ORDER BY clause inside the function call.
-- To guarantee deterministic ordering, we pre-sort rows in a subquery (ordered_sessions)
-- before aggregating. SQLite preserves insertion/scan order within GROUP_CONCAT when
-- the input is already sorted.

DROP TABLE IF EXISTS journey_paths;

CREATE TABLE journey_paths AS
WITH first_conversion AS (
    SELECT full_visitor_id, MIN(visit_id) AS min_conv_visit_id
    FROM fact_conversions
    GROUP BY full_visitor_id
),
scoped_sessions AS (
    SELECT 
        s.full_visitor_id,
        s.visit_id,
        s.channel_grouping,
        CASE WHEN fc.min_conv_visit_id IS NOT NULL THEN 1 ELSE 0 END AS converted
    FROM fact_sessions s
    LEFT JOIN first_conversion fc ON s.full_visitor_id = fc.full_visitor_id
    WHERE fc.min_conv_visit_id IS NULL OR s.visit_id <= fc.min_conv_visit_id
),
ordered_sessions AS (
    SELECT *
    FROM scoped_sessions
    ORDER BY full_visitor_id, visit_id, channel_grouping
)
SELECT 
    full_visitor_id,
    GROUP_CONCAT(channel_grouping, ' > ') AS touchpoint_path,
    MAX(converted) AS converted
FROM ordered_sessions
GROUP BY full_visitor_id;
