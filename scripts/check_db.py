"""Check pltm_mcp.db state and diagnose knowledge_add_concept hang."""
import os
import sqlite3

db = r"C:\Users\alber\CascadeProjects\pltm-mcp\pltm_mcp.db"
wal = db + "-wal"
shm = db + "-shm"

print(f"DB:  {os.path.getsize(db):,} bytes")
print(f"WAL: {os.path.getsize(wal):,} bytes" if os.path.exists(wal) else "WAL: not present")
print(f"SHM: {os.path.getsize(shm):,} bytes" if os.path.exists(shm) else "SHM: not present")

conn = sqlite3.connect(db, timeout=5)

# Journal mode
cur = conn.execute("PRAGMA journal_mode")
print(f"Journal mode: {cur.fetchone()[0]}")

# All tables
cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f"Tables: {tables}")

# Check if knowledge tables exist
has_kg = any("knowledge" in t for t in tables)
print(f"Knowledge tables exist: {has_kg}")

# Row counts
for t in tables:
    try:
        cur = conn.execute(f"SELECT COUNT(*) FROM [{t}]")
        print(f"  {t}: {cur.fetchone()[0]} rows")
    except Exception as e:
        print(f"  {t}: ERROR - {e}")

# Try WAL checkpoint
try:
    result = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    print(f"WAL checkpoint: {result}")
except Exception as e:
    print(f"WAL checkpoint failed: {e}")

# Try creating knowledge tables manually to test
try:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_nodes (
            node_id TEXT PRIMARY KEY,
            concept TEXT NOT NULL,
            domain TEXT NOT NULL,
            connections INTEGER DEFAULT 0,
            value_score REAL DEFAULT 0.0,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_node TEXT NOT NULL,
            to_node TEXT NOT NULL,
            relationship TEXT NOT NULL,
            strength REAL DEFAULT 0.5,
            bidirectional INTEGER DEFAULT 0,
            UNIQUE(from_node, to_node, relationship)
        )
    """)
    conn.commit()
    print("Knowledge tables created/verified: OK")
except Exception as e:
    print(f"Knowledge table creation FAILED: {e}")

conn.close()
print("Done.")
