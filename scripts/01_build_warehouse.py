"""
01_build_warehouse.py
Executes the SQL warehouse layer scripts against the raw session data in SQLite.

Design Decision: We use SQLite as the analytical warehouse engine. The raw staging CSV
(extracted once from BigQuery via 00_extract_bigquery.py) is loaded into a single
authoritative staging_sessions table. All downstream SQL scripts read from this table.
There is exactly one copy of the data; no parallel PostgreSQL or BigQuery dependency.

Verifies Section 5 checkpoints and exports tables to CSV for Tableau and downstream modeling.
"""

import os
import sqlite3
import pandas as pd

def build_warehouse():
    db_path = 'data/warehouse.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        
    print(f"Creating database: {db_path}")
    con = sqlite3.connect(db_path)
    
    raw_path = 'data/raw/staging_sessions.csv'
    if not os.path.exists(raw_path):
        print(f"ERROR: {raw_path} not found. Run scripts/00_extract_bigquery.py first.")
        return
    
    print(f"Loading {raw_path} into staging_sessions table...")
    df_raw = pd.read_csv(raw_path, dtype={'full_visitor_id': str, 'visit_id': int})
    df_raw.to_sql('staging_sessions', con, index=False, if_exists='replace')
    
    raw_count = len(df_raw)
    null_channels = df_raw['channel_grouping'].isna().sum()
    print(f"  Loaded {raw_count:,} rows. NULL channel_grouping count: {null_channels}")
    if null_channels > 0:
        print(f"  WARNING: {null_channels} rows have NULL channel_grouping.")
    
    sql_files = [
        'sql/01_dim_channel.sql',
        'sql/02_fact_sessions.sql',
        'sql/03_fact_conversions.sql',
        'sql/04_fact_channel_transitions.sql',
        'sql/05_journey_paths.sql'
    ]
    
    for sql_file in sql_files:
        print(f"Executing {sql_file}...")
        with open(sql_file, 'r') as f:
            sql_script = f.read()
        con.executescript(sql_script)
        
    print("\n==========================================")
    print("  SECTION 5 VERIFICATION CHECKPOINTS")
    print("==========================================")
    
    # Checkpoint 1: fact_sessions — should match raw staging count exactly
    c_sessions = con.execute("SELECT COUNT(*) FROM fact_sessions").fetchone()[0]
    match_raw = "MATCH" if c_sessions == raw_count else f"MISMATCH (raw={raw_count:,})"
    print(f"[fact_sessions]            Row count: {c_sessions:,} — {match_raw}")
    
    # Checkpoint 2: fact_conversions
    c_conv = con.execute("SELECT COUNT(*) FROM fact_conversions").fetchone()[0]
    total_txns = con.execute("SELECT SUM(transactions) FROM fact_conversions").fetchone()[0]
    total_rev = con.execute("SELECT SUM(revenue) FROM fact_conversions").fetchone()[0]
    real_aov = total_rev / total_txns if total_txns > 0 else 0
    print(f"[fact_conversions]         Row count: {c_conv:,}")
    print(f"                           Total transactions: {total_txns:,}")
    print(f"                           Total revenue: ${total_rev:,.2f}")
    print(f"                           Real AOV: ${real_aov:.2f}")
    
    # Checkpoint 3: dim_channel
    channels = con.execute("SELECT channel_grouping FROM dim_channel").fetchall()
    ch_list = [c[0] for c in channels]
    print(f"[dim_channel]              Channels ({len(ch_list)}): {ch_list}")
    
    # Checkpoint 4: fact_channel_transitions
    c_trans = con.execute("SELECT SUM(transition_count) FROM fact_channel_transitions").fetchone()[0]
    print(f"[fact_channel_transitions] Total edges: {c_trans:,}")
    print("\nTop 10 Channel Transitions:")
    top_trans = pd.read_sql("SELECT * FROM fact_channel_transitions ORDER BY transition_count DESC LIMIT 10", con)
    print(top_trans.to_string(index=False))
    
    # Checkpoint 5: journey_paths
    c_paths = con.execute("SELECT COUNT(*), SUM(converted) FROM journey_paths").fetchone()
    print(f"\n[journey_paths]            Distinct visitors: {c_paths[0]:,} | Converting paths: {c_paths[1]:,}")
    
    # Spot-check a few journey paths for sanity
    print("\nSample converting journey paths:")
    sample_paths = pd.read_sql("SELECT * FROM journey_paths WHERE converted = 1 LIMIT 5", con)
    for _, row in sample_paths.iterrows():
        print(f"  {row['touchpoint_path']}")
    
    print("\n==========================================")
    print("  EXPORTING CSVs")
    print("==========================================")
    os.makedirs('data/exports', exist_ok=True)
    
    tables_to_export = ['dim_channel', 'fact_sessions', 'fact_conversions', 'fact_channel_transitions', 'journey_paths']
    for table in tables_to_export:
        export_path = f'data/exports/{table}.csv'
        df_table = pd.read_sql(f"SELECT * FROM {table}", con)
        df_table.to_csv(export_path, index=False)
        print(f"Exported: {export_path} ({len(df_table):,} rows)")
        
    con.close()
    print("\nWarehouse build complete.\n")

if __name__ == '__main__':
    build_warehouse()
