"""
Backfill embeddings for all typed memories that don't have them yet.
Processes in batches of 32 to avoid memory issues.
"""

import sqlite3
import time
import numpy as np

DB_PATH = "data/pltm_mcp.db"
BATCH_SIZE = 32


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")

    # Get all memory IDs that need embedding
    all_mems = conn.execute(
        "SELECT id, content, trigger, action FROM typed_memories"
    ).fetchall()

    existing = set(r[0] for r in conn.execute(
        "SELECT memory_id FROM memory_embeddings"
    ).fetchall())

    to_index = []
    for mid, content, trigger, action in all_mems:
        if mid in existing:
            continue
        text = content or ""
        if trigger:
            text += f" | trigger: {trigger}"
        if action:
            text += f" | action: {action}"
        to_index.append((mid, text))

    print(f"Total memories: {len(all_mems)}")
    print(f"Already indexed: {len(existing)}")
    print(f"Need indexing: {len(to_index)}")

    if not to_index:
        print("Nothing to do!")
        conn.close()
        return

    # Lazy-load model
    print("Loading embedding model...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("Model loaded.")

    indexed = 0
    t0 = time.time()

    for i in range(0, len(to_index), BATCH_SIZE):
        batch = to_index[i:i + BATCH_SIZE]
        texts = [t[1] for t in batch]
        ids = [t[0] for t in batch]

        vecs = model.encode(texts, normalize_embeddings=True, batch_size=BATCH_SIZE)

        for j, (mid, text) in enumerate(batch):
            blob = vecs[j].astype(np.float32).tobytes()
            content_hash = str(hash(text))
            conn.execute(
                """INSERT OR REPLACE INTO memory_embeddings
                   (memory_id, embedding, content_hash, indexed_at)
                   VALUES (?, ?, ?, ?)""",
                (mid, blob, content_hash, time.time())
            )

        conn.commit()
        indexed += len(batch)
        elapsed = time.time() - t0
        rate = indexed / elapsed if elapsed > 0 else 0
        print(f"  Indexed {indexed}/{len(to_index)} ({rate:.0f}/s)")

    elapsed = time.time() - t0
    print(f"\nDone! Indexed {indexed} memories in {elapsed:.1f}s")

    # Verify
    total_emb = conn.execute("SELECT COUNT(*) FROM memory_embeddings").fetchone()[0]
    print(f"Total embeddings in DB: {total_emb}")
    conn.close()


if __name__ == "__main__":
    main()
