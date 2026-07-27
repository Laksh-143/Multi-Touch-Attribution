"""
00_extract_bigquery.py
One-time extraction of GA sample session data from Google BigQuery into local CSV.
This decouples the downstream SQLite warehouse from BigQuery so all modeling runs locally.

Prerequisites:
    pip install google-cloud-bigquery db-dtypes pyarrow
    gcloud auth application-default login --project=multi-touch-attribution-503505

If either dependency is missing or auth has not been configured, the script will fail
with a clear error message before attempting the query.
"""

import os
import sys

def check_dependencies():
    """Verify required packages are installed before attempting BigQuery connection."""
    missing = []
    for pkg in ['google.cloud.bigquery', 'db_dtypes', 'pyarrow']:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg.replace('.', '-'))
    
    if missing:
        print("ERROR: Missing required packages:")
        print(f"  pip install {' '.join(missing)}")
        sys.exit(1)

def extract_session_data():
    check_dependencies()
    
    from google.cloud import bigquery
    import pandas as pd
    
    project_id = 'multi-touch-attribution-503505'
    
    print(f"Connecting to Google BigQuery (project: {project_id})...")
    print("If this fails with an auth error, run:")
    print(f"  gcloud auth application-default login --project={project_id}\n")
    
    client = bigquery.Client(project=project_id)
    
    query = """
    SELECT 
        fullVisitorId AS full_visitor_id,
        visitId AS visit_id,
        channelGrouping AS channel_grouping,
        IFNULL(totals.transactions, 0) AS transactions,
        IFNULL(totals.totalTransactionRevenue, 0) / 1000000.0 AS revenue
    FROM 
        `bigquery-public-data.google_analytics_sample.ga_sessions_*`
    WHERE 
        _TABLE_SUFFIX BETWEEN '20161101' AND '20170228'
    """
    
    print("Executing extraction query for 4-month window (Nov 1, 2016 - Feb 28, 2017)...")
    df = client.query(query).to_dataframe()
    
    df = df.sort_values(['full_visitor_id', 'visit_id']).reset_index(drop=True)
    
    os.makedirs('data/raw', exist_ok=True)
    output_path = 'data/raw/staging_sessions.csv'
    df.to_csv(output_path, index=False)
    
    total_sessions = len(df)
    converting_sessions = len(df[df['transactions'] >= 1])
    conv_rate = (converting_sessions / total_sessions) * 100 if total_sessions > 0 else 0
    null_channels = df['channel_grouping'].isna().sum()
    
    print("\n--- EXTRACTION COMPLETE ---")
    print(f"File Saved:          {output_path}")
    print(f"Total Sessions:      {total_sessions:,}")
    print(f"Converting Sessions: {converting_sessions:,} ({conv_rate:.2f}%)")
    print(f"Unique Visitors:     {df['full_visitor_id'].nunique():,}")
    print(f"NULL channel_grouping: {null_channels}")
    print(f"Channels Present:    {sorted(df['channel_grouping'].unique().tolist())}")
    print("---------------------------\n")

if __name__ == '__main__':
    extract_session_data()
