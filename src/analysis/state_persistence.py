"""
State Persistence System

Persists arbitrary key-value state across conversations.
Enables work continuity — save analysis progress, resume later.
All state stored in SQLite alongside PLTM data.
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class StatePersistence:
    """Save and load state across conversations."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).parent.parent.parent / "data" / "pltm_mcp.db"
        self._ensure_tables()
    
    def _ensure_tables(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                access_count INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_state_cat ON conversation_state(category)")
        conn.commit()
        conn.close()
    
    def save(self, key: str, value: Any, category: str = "general", metadata: Optional[Dict] = None) -> Dict:
        """Save state that persists across conversations"""
        now = time.time()
        conn = sqlite3.connect(str(self.db_path))
        
        # Check if exists
        cursor = conn.execute("SELECT created_at FROM conversation_state WHERE key = ?", (key,))
        existing = cursor.fetchone()
        
        if existing:
            conn.execute(
                "UPDATE conversation_state SET value = ?, category = ?, updated_at = ?, metadata = ? WHERE key = ?",
                (json.dumps(value, default=str), category, now, json.dumps(metadata or {}), key)
            )
            action = "updated"
        else:
            conn.execute(
                "INSERT INTO conversation_state (key, value, category, created_at, updated_at, metadata) VALUES (?,?,?,?,?,?)",
                (key, json.dumps(value, default=str), category, now, now, json.dumps(metadata or {}))
            )
            action = "created"
        
        conn.commit()
        conn.close()
        return {"ok": True, "key": key, "action": action, "category": category}
    
    def load(self, key: str) -> Dict:
        """Load persisted state"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            "SELECT value, category, created_at, updated_at, access_count, metadata FROM conversation_state WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {"ok": False, "err": f"No state found for key '{key}'"}
        
        # Increment access count
        conn.execute(
            "UPDATE conversation_state SET access_count = access_count + 1 WHERE key = ?",
            (key,)
        )
        conn.commit()
        conn.close()
        
        return {
            "ok": True,
            "key": key,
            "value": json.loads(row[0]),
            "category": row[1],
            "created_at": row[2],
            "updated_at": row[3],
            "access_count": row[4] + 1,
            "metadata": json.loads(row[5]) if row[5] else {},
        }
    
    def list_states(self, category: Optional[str] = None) -> Dict:
        """List all saved states"""
        conn = sqlite3.connect(str(self.db_path))
        
        if category:
            cursor = conn.execute(
                "SELECT key, category, updated_at, access_count FROM conversation_state WHERE category = ? ORDER BY updated_at DESC",
                (category,)
            )
        else:
            cursor = conn.execute(
                "SELECT key, category, updated_at, access_count FROM conversation_state ORDER BY updated_at DESC"
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        states = [{"key": r[0], "category": r[1], "updated": r[2], "accesses": r[3]} for r in rows]
        return {"ok": True, "n": len(states), "states": states}
    
    def delete(self, key: str) -> Dict:
        """Delete a saved state"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("DELETE FROM conversation_state WHERE key = ?", (key,))
        conn.commit()
        conn.close()
        return {"ok": True, "deleted": key}
