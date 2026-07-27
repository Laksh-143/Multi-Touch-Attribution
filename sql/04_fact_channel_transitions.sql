-- 04_fact_channel_transitions.sql
-- Builds the Markov Chain transition matrix directly within SQL.
--
-- Attribution Window Rationale:
-- A user's journey is truncated at their first converting session (scoped_sessions CTE). 
-- Post-conversion browsing sessions are excluded from attribution for that conversion event.
--
-- Transition Logic:
-- 1. Start edges: The initial touchpoint for each visitor transitions from a synthetic 'Start' state.
-- 2. Mid-path edges: LAG(channel_grouping) identifies step-by-step channel transitions.
-- 3. End edges: The final touchpoint in the scoped window transitions to 'Conversion' (if converted) or 'Null' (drop-off).

DROP TABLE IF EXISTS fact_channel_transitions;

CREATE TABLE fact_channel_transitions AS
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
        ROW_NUMBER() OVER (PARTITION BY s.full_visitor_id ORDER BY s.visit_id, s.channel_grouping) AS seq_asc,
        ROW_NUMBER() OVER (PARTITION BY s.full_visitor_id ORDER BY s.visit_id DESC, s.channel_grouping DESC) AS seq_desc,
        CASE WHEN fc.min_conv_visit_id IS NOT NULL THEN 1 ELSE 0 END AS user_converted
    FROM fact_sessions s
    LEFT JOIN first_conversion fc ON s.full_visitor_id = fc.full_visitor_id
    WHERE fc.min_conv_visit_id IS NULL OR s.visit_id <= fc.min_conv_visit_id
),
mid_path_edges AS (
    SELECT 
        full_visitor_id,
        LAG(channel_grouping) OVER (PARTITION BY full_visitor_id ORDER BY visit_id, channel_grouping) AS from_channel,
        channel_grouping AS to_channel
    FROM scoped_sessions
),
all_edges AS (
    -- Start edges: from 'Start' to the user's first touchpoint
    SELECT 'Start' AS from_channel, channel_grouping AS to_channel, 1 AS edge_count
    FROM scoped_sessions
    WHERE seq_asc = 1
    
    UNION ALL
    
    -- Mid-path edges: from previous channel to current channel
    SELECT from_channel, to_channel, 1 AS edge_count
    FROM mid_path_edges
    WHERE from_channel IS NOT NULL
    
    UNION ALL
    
    -- End edges: from final touchpoint to 'Conversion' or 'Null'
    SELECT 
        channel_grouping AS from_channel, 
        CASE WHEN user_converted = 1 THEN 'Conversion' ELSE 'Null' END AS to_channel,
        1 AS edge_count
    FROM scoped_sessions
    WHERE seq_desc = 1
)
SELECT 
    from_channel,
    to_channel,
    SUM(edge_count) AS transition_count
FROM all_edges
GROUP BY from_channel, to_channel
ORDER BY from_channel, transition_count DESC;
