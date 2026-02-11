import sqlite3
import os

db_path = r"C:\Users\alber\CascadeProjects\LLTM\data\pltm_mcp.db"
print(f"Size: {os.path.getsize(db_path):,} bytes")

conn = sqlite3.connect(db_path)
cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f"Tables: {tables}")

for t in tables:
    try:
        count = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
        print(f"  {t}: {count} rows")
    except Exception as e:
        print(f"  {t}: ERROR - {e}")

conn.close()
