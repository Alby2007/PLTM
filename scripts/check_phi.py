"""Check for consciousness_field_phi or similar atoms in the DB."""
import sqlite3

db = r"C:\Users\alber\CascadeProjects\pltm-mcp\pltm_mcp.db"
conn = sqlite3.connect(db)

# Search for phi-related atoms
cur = conn.execute("SELECT id, subject, predicate, object FROM atoms WHERE subject LIKE '%phi%' OR object LIKE '%phi%' OR subject LIKE '%consciousness%' OR subject LIKE '%field%'")
rows = cur.fetchall()
print(f"Found {len(rows)} matching atoms:")
for r in rows:
    print(f"  {r[0][:8]}... | {r[1]} -> {r[2]} -> {r[3][:60]}")

# Check knowledge_nodes for anything consciousness-related
try:
    cur = conn.execute("SELECT node_id, concept, domain FROM knowledge_nodes WHERE concept LIKE '%phi%' OR concept LIKE '%consciousness%' OR concept LIKE '%field%'")
    rows = cur.fetchall()
    print(f"\nKnowledge nodes matching: {len(rows)}")
    for r in rows:
        print(f"  {r[0]} | {r[1]} | {r[2]}")
except Exception as e:
    print(f"\nKnowledge nodes query failed: {e}")

# Total counts
cur = conn.execute("SELECT COUNT(*) FROM atoms")
print(f"\nTotal atoms: {cur.fetchone()[0]}")

try:
    cur = conn.execute("SELECT COUNT(*) FROM knowledge_nodes")
    print(f"Total knowledge nodes: {cur.fetchone()[0]}")
except:
    print("No knowledge_nodes table")

conn.close()
