"""
Indicator Tracker & Alerting System

Tracks named indicators with thresholds, stores history, and flags breaches.
Indicators are updated by Claude via MCP tools and checked on demand.
"""

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class Indicator:
    indicator_id: str
    name: str
    domain: str
    current_value: float
    threshold: float
    direction: str  # "above" = alert when value > threshold, "below" = alert when value < threshold
    status: str  # "normal", "warning", "breached"
    check_frequency: str  # "daily", "weekly", "monthly"
    last_checked: float
    created_at: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class IndicatorTracker:
    """Track indicators with thresholds and alert on breach."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).parent.parent.parent / "data" / "pltm_mcp.db"
        self._ensure_tables()
    
    def _ensure_tables(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS indicators (
                indicator_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                domain TEXT NOT NULL,
                current_value REAL DEFAULT 0.0,
                threshold REAL NOT NULL,
                direction TEXT DEFAULT 'above',
                status TEXT DEFAULT 'normal',
                check_frequency TEXT DEFAULT 'weekly',
                last_checked REAL,
                created_at REAL NOT NULL,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS indicator_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                indicator_id TEXT NOT NULL,
                value REAL NOT NULL,
                status TEXT NOT NULL,
                note TEXT DEFAULT '',
                timestamp REAL NOT NULL,
                FOREIGN KEY (indicator_id) REFERENCES indicators(indicator_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ind_hist ON indicator_history(indicator_id, timestamp)")
        conn.commit()
        conn.close()
    
    def create_indicator(self, indicator_id: str, name: str, domain: str,
                         threshold: float, direction: str = "above",
                         check_frequency: str = "weekly",
                         initial_value: float = 0.0,
                         metadata: Optional[Dict] = None) -> Dict:
        """Create a new tracked indicator"""
        now = time.time()
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                "INSERT OR REPLACE INTO indicators (indicator_id, name, domain, current_value, threshold, direction, status, check_frequency, last_checked, created_at, metadata) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (indicator_id, name, domain, initial_value, threshold, direction,
                 "normal", check_frequency, now, now, json.dumps(metadata or {}))
            )
            conn.execute(
                "INSERT INTO indicator_history (indicator_id, value, status, note, timestamp) VALUES (?,?,?,?,?)",
                (indicator_id, initial_value, "normal", "created", now)
            )
            conn.commit()
            return {"ok": True, "id": indicator_id, "threshold": threshold, "direction": direction}
        except Exception as e:
            return {"ok": False, "err": str(e)}
        finally:
            conn.close()
    
    def update_indicator(self, indicator_id: str, value: float, note: str = "") -> Dict:
        """Update an indicator's value and check threshold"""
        now = time.time()
        conn = sqlite3.connect(str(self.db_path))
        
        cursor = conn.execute("SELECT threshold, direction, status FROM indicators WHERE indicator_id = ?", (indicator_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"ok": False, "err": f"Indicator '{indicator_id}' not found"}
        
        threshold, direction, old_status = row
        
        # Check breach
        if direction == "above":
            breached = value >= threshold
        else:
            breached = value <= threshold
        
        new_status = "breached" if breached else ("warning" if abs(value - threshold) / max(threshold, 0.01) < 0.1 else "normal")
        
        alert = None
        if new_status == "breached" and old_status != "breached":
            alert = {"type": "THRESHOLD_BREACH", "indicator": indicator_id,
                     "value": value, "threshold": threshold, "direction": direction}
        
        conn.execute(
            "UPDATE indicators SET current_value = ?, status = ?, last_checked = ? WHERE indicator_id = ?",
            (value, new_status, now, indicator_id)
        )
        conn.execute(
            "INSERT INTO indicator_history (indicator_id, value, status, note, timestamp) VALUES (?,?,?,?,?)",
            (indicator_id, value, new_status, note, now)
        )
        conn.commit()
        conn.close()
        
        result = {"ok": True, "id": indicator_id, "value": value, "status": new_status}
        if alert:
            result["alert"] = alert
        return result
    
    def check_all(self) -> Dict:
        """Check all indicators and return status + any breaches"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute("SELECT indicator_id, name, domain, current_value, threshold, direction, status, check_frequency, last_checked FROM indicators ORDER BY domain, name")
        rows = cursor.fetchall()
        conn.close()
        
        indicators = []
        breaches = []
        stale = []
        now = time.time()
        
        freq_seconds = {"daily": 86400, "weekly": 604800, "monthly": 2592000}
        
        for r in rows:
            ind = {
                "id": r[0], "name": r[1], "domain": r[2],
                "value": r[3], "threshold": r[4], "direction": r[5],
                "status": r[6], "frequency": r[7],
            }
            indicators.append(ind)
            
            if r[6] == "breached":
                breaches.append(ind)
            
            max_age = freq_seconds.get(r[7], 604800)
            if now - r[8] > max_age:
                stale.append({"id": r[0], "name": r[1], "last_checked_ago_hours": round((now - r[8]) / 3600, 1)})
        
        return {
            "total": len(indicators),
            "breached": len(breaches),
            "stale": len(stale),
            "indicators": indicators,
            "alerts": breaches,
            "needs_update": stale,
        }
    
    def get_history(self, indicator_id: str, limit: int = 30) -> List[Dict]:
        """Get value history for an indicator"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            "SELECT value, status, note, timestamp FROM indicator_history WHERE indicator_id = ? ORDER BY timestamp DESC LIMIT ?",
            (indicator_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        return [{"value": r[0], "status": r[1], "note": r[2], "ts": r[3]} for r in rows]
    
    def delete_indicator(self, indicator_id: str) -> Dict:
        """Remove an indicator and its history"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("DELETE FROM indicator_history WHERE indicator_id = ?", (indicator_id,))
        conn.execute("DELETE FROM indicators WHERE indicator_id = ?", (indicator_id,))
        conn.commit()
        conn.close()
        return {"ok": True, "deleted": indicator_id}
