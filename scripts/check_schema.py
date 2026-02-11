import sqlite3

conn = sqlite3.connect(r"C:\Users\alber\CascadeProjects\LLTM\data\pltm_mcp.db")

tables = ["self_communication", "self_curiosity", "self_values", "self_reasoning", "prediction_book"]
for t in tables:
    cols = conn.execute(f"PRAGMA table_info({t})").fetchall()
    print(f"\n=== {t} ===")
    for c in cols:
        print(f"  {c[1]} ({c[2]})")

conn.close()
