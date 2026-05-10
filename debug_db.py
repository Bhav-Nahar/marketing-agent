"""Quick diagnostic script to inspect what's actually in the DuckDB database."""
import duckdb
import glob
import os

# Find all duckdb files in the project
db_files = glob.glob("*.duckdb")
print(f"Found DuckDB files: {db_files}\n")

for db_file in db_files:
    print(f"{'='*60}")
    print(f"DATABASE: {db_file}")
    print(f"{'='*60}")
    
    con = duckdb.connect(db_file, read_only=True)
    
    # Show all schemas
    print("\n--- SCHEMAS ---")
    schemas = con.execute("SELECT schema_name FROM information_schema.schemata").fetchall()
    for s in schemas:
        print(f"  {s[0]}")
    
    # Show all tables with their schema
    print("\n--- ALL TABLES ---")
    tables = con.execute("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
        ORDER BY table_schema, table_name
    """).fetchall()
    for schema, table in tables:
        print(f"  {schema}.{table}")
    
    # For each table, show row count and sample
    for schema, table in tables:
        if table.startswith('_dlt'): 
            continue
        full_name = f'"{schema}"."{table}"'
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {full_name}").fetchone()[0]
            print(f"\n--- {full_name}: {count} rows ---")
            if count > 0:
                cols = con.execute(f"SELECT * FROM {full_name} LIMIT 1").description
                col_names = [c[0] for c in cols]
                print(f"  Columns: {col_names}")
                
                # Check for specific columns we care about
                if 'campaign_name' in col_names:
                    print(f"  ✅ campaign_name exists")
                if 'purchases' in col_names:
                    print(f"  ✅ purchases column exists (flattened)")
                if 'purchase_value' in col_names:
                    print(f"  ✅ purchase_value column exists (flattened)")
                    
                # Show date range
                if 'date_start' in col_names:
                    date_range = con.execute(f"SELECT MIN(date_start), MAX(date_start) FROM {full_name}").fetchone()
                    print(f"  Date range: {date_range[0]} to {date_range[1]}")
                    
                # Show a sample row
                sample = con.execute(f"SELECT * FROM {full_name} LIMIT 1").fetchone()
                print(f"  Sample: {dict(zip(col_names, sample))}")
        except Exception as e:
            print(f"  ERROR querying {full_name}: {e}")
    
    con.close()

print("\n\n--- SQLITE USER STATE ---")
import sqlite3
state_db = os.path.join("db", "mvp_state.db")
if os.path.exists(state_db):
    conn = sqlite3.connect(state_db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM user_state").fetchall()
    for row in rows:
        d = dict(row)
        d['long_lived_token'] = d['long_lived_token'][:20] + '...' if d.get('long_lived_token') else None
        print(f"  {d}")
    conn.close()
else:
    print(f"  State DB not found at {state_db}")
