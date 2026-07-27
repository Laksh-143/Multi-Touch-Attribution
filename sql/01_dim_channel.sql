-- 01_dim_channel.sql
-- Reference table of distinct channel_grouping values present in the Google Analytics taxonomy.
-- Primary key: channel_grouping

DROP TABLE IF EXISTS dim_channel;

CREATE TABLE dim_channel AS
SELECT DISTINCT channel_grouping 
FROM staging_sessions
WHERE channel_grouping IS NOT NULL
ORDER BY channel_grouping;
