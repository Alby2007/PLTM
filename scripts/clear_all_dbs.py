"""Clear all pltm_mcp.db files of all data."""
import sqlite3
import os

dbs = [
    r"C:\Users\alber\CascadeProjects\LLTM\pltm_mcp.db",
    r"C:\Users\alber\CascadeProjects\LLTM\mcp_server\pltm_mcp.db",
    r"C:\Users\alber\CascadeProjects\pltm-mcp\pltm_mcp.db",
]

for db_path in dbs:
    if not os.path.exists(db_path):
        print(f"  SKIP (not found): {db_path}")
        continue
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        for t in tables:
            if "fts" not in t and t != "sqlite_sequence":
                conn.execute(f"DELETE FROM [{t}]")
        conn.commit()
        # Verify
        count = conn.execute("SELECT COUNT(*) FROM atoms").fetchone()[0]
        print(f"  CLEARED: {db_path} (atoms={count}, tables wiped: {[t for t in tables if 'fts' not in t and t != 'sqlite_sequence']})")
        # Remove WAL/SHM
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
        for ext in ["-wal", "-shm"]:
            f = db_path + ext
            if os.path.exists(f):
                os.remove(f)
                print(f"    Removed {f}")
    except Exception as e:
        print(f"  ERROR: {db_path} -> {e}")

print("\nAll databases cleared. Ready for fresh db from Mac.")
