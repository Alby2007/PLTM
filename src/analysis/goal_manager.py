"""
Goal Management System

Persistent goal tracking with plans, progress, and status.
Enables autonomous goal-directed behavior across conversations.
"""

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class GoalManager:
    """Create, track, and manage goals with plans."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).parent.parent.parent / "data" / "pltm_mcp.db"
        self._ensure_tables()
    
    def _ensure_tables(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                goal_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                status TEXT DEFAULT 'active',
                priority TEXT DEFAULT 'medium',
                progress REAL DEFAULT 0.0,
                success_criteria TEXT DEFAULT '[]',
                plan TEXT DEFAULT '[]',
                blockers TEXT DEFAULT '[]',
                parent_goal_id TEXT,
                deadline TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                completed_at REAL,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS goal_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT DEFAULT '',
                timestamp REAL NOT NULL,
                FOREIGN KEY (goal_id) REFERENCES goals(goal_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_goals_cat ON goals(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_goal_log ON goal_log(goal_id, timestamp)")
        conn.commit()
        conn.close()
    
    def create_goal(self, title: str, description: str, category: str = "general",
                    priority: str = "medium", success_criteria: Optional[List[str]] = None,
                    plan: Optional[List[Dict]] = None, deadline: Optional[str] = None,
                    parent_goal_id: Optional[str] = None,
                    metadata: Optional[Dict] = None) -> Dict:
        """Create a new goal with optional plan"""
        goal_id = f"goal_{uuid.uuid4().hex[:8]}"
        now = time.time()
        
        plan_items = plan or []
        for i, step in enumerate(plan_items):
            if "id" not in step:
                step["id"] = f"step_{i}"
            if "status" not in step:
                step["status"] = "pending"
        
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            """INSERT INTO goals (goal_id, title, description, category, status, priority,
               progress, success_criteria, plan, blockers, parent_goal_id, deadline,
               created_at, updated_at, metadata)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (goal_id, title, description, category, "active", priority,
             0.0, json.dumps(success_criteria or []), json.dumps(plan_items),
             "[]", parent_goal_id, deadline, now, now, json.dumps(metadata or {}))
        )
        conn.execute(
            "INSERT INTO goal_log (goal_id, action, details, timestamp) VALUES (?,?,?,?)",
            (goal_id, "created", title, now)
        )
        conn.commit()
        conn.close()
        
        return {"ok": True, "goal_id": goal_id, "title": title, "status": "active",
                "plan_steps": len(plan_items)}
    
    def update_goal(self, goal_id: str, progress: Optional[float] = None,
                    status: Optional[str] = None, add_blocker: Optional[str] = None,
                    remove_blocker: Optional[str] = None,
                    complete_step: Optional[str] = None,
                    add_step: Optional[Dict] = None,
                    note: str = "") -> Dict:
        """Update goal progress, status, blockers, or plan steps"""
        now = time.time()
        conn = sqlite3.connect(str(self.db_path))
        
        cursor = conn.execute("SELECT * FROM goals WHERE goal_id = ?", (goal_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"ok": False, "err": f"Goal '{goal_id}' not found"}
        
        # Get column names
        cols = [d[0] for d in cursor.description]
        goal = dict(zip(cols, row))
        
        changes = []
        
        if progress is not None:
            conn.execute("UPDATE goals SET progress = ?, updated_at = ? WHERE goal_id = ?",
                        (min(1.0, max(0.0, progress)), now, goal_id))
            changes.append(f"progress={progress:.0%}")
        
        if status:
            conn.execute("UPDATE goals SET status = ?, updated_at = ? WHERE goal_id = ?",
                        (status, now, goal_id))
            if status == "completed":
                conn.execute("UPDATE goals SET completed_at = ? WHERE goal_id = ?", (now, goal_id))
            changes.append(f"status={status}")
        
        if add_blocker:
            blockers = json.loads(goal["blockers"])
            blockers.append({"text": add_blocker, "added": now})
            conn.execute("UPDATE goals SET blockers = ?, updated_at = ? WHERE goal_id = ?",
                        (json.dumps(blockers), now, goal_id))
            changes.append(f"blocker_added")
        
        if remove_blocker:
            blockers = json.loads(goal["blockers"])
            blockers = [b for b in blockers if b.get("text") != remove_blocker]
            conn.execute("UPDATE goals SET blockers = ?, updated_at = ? WHERE goal_id = ?",
                        (json.dumps(blockers), now, goal_id))
            changes.append(f"blocker_removed")
        
        if complete_step:
            plan = json.loads(goal["plan"])
            for step in plan:
                if step.get("id") == complete_step:
                    step["status"] = "completed"
                    step["completed_at"] = now
            # Auto-calculate progress from plan
            total = len(plan)
            done = sum(1 for s in plan if s.get("status") == "completed")
            auto_progress = done / total if total > 0 else 0
            conn.execute("UPDATE goals SET plan = ?, progress = ?, updated_at = ? WHERE goal_id = ?",
                        (json.dumps(plan), auto_progress, now, goal_id))
            changes.append(f"step_{complete_step}_done")
        
        if add_step:
            plan = json.loads(goal["plan"])
            if "id" not in add_step:
                add_step["id"] = f"step_{len(plan)}"
            if "status" not in add_step:
                add_step["status"] = "pending"
            plan.append(add_step)
            conn.execute("UPDATE goals SET plan = ?, updated_at = ? WHERE goal_id = ?",
                        (json.dumps(plan), now, goal_id))
            changes.append(f"step_added")
        
        log_detail = f"{', '.join(changes)}"
        if note:
            log_detail += f" | {note}"
        conn.execute(
            "INSERT INTO goal_log (goal_id, action, details, timestamp) VALUES (?,?,?,?)",
            (goal_id, "updated", log_detail, now)
        )
        conn.commit()
        conn.close()
        
        return {"ok": True, "goal_id": goal_id, "changes": changes}
    
    def get_goals(self, status: Optional[str] = None, category: Optional[str] = None,
                  include_plan: bool = True, include_log: bool = False) -> Dict:
        """Get all goals, optionally filtered"""
        conn = sqlite3.connect(str(self.db_path))
        
        query = "SELECT * FROM goals"
        params = []
        conditions = []
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        if category:
            conditions.append("category = ?")
            params.append(category)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY priority DESC, updated_at DESC"
        
        cursor = conn.execute(query, params)
        cols = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        
        goals = []
        for row in rows:
            g = dict(zip(cols, row))
            goal_out = {
                "id": g["goal_id"],
                "title": g["title"],
                "description": g["description"][:100],
                "category": g["category"],
                "status": g["status"],
                "priority": g["priority"],
                "progress": g["progress"],
                "blockers": json.loads(g["blockers"]),
                "deadline": g["deadline"],
                "updated": g["updated_at"],
            }
            
            if include_plan:
                plan = json.loads(g["plan"])
                goal_out["plan"] = plan
                goal_out["plan_summary"] = {
                    "total": len(plan),
                    "done": sum(1 for s in plan if s.get("status") == "completed"),
                    "in_progress": sum(1 for s in plan if s.get("status") == "in_progress"),
                    "pending": sum(1 for s in plan if s.get("status") == "pending"),
                }
            
            if include_log:
                log_cursor = conn.execute(
                    "SELECT action, details, timestamp FROM goal_log WHERE goal_id = ? ORDER BY timestamp DESC LIMIT 10",
                    (g["goal_id"],)
                )
                goal_out["log"] = [{"action": r[0], "details": r[1], "ts": r[2]} for r in log_cursor.fetchall()]
            
            goals.append(goal_out)
        
        conn.close()
        
        # Summary
        active = sum(1 for g in goals if g["status"] == "active")
        blocked = sum(1 for g in goals if g.get("blockers"))
        
        return {
            "ok": True,
            "n": len(goals),
            "active": active,
            "blocked": blocked,
            "goals": goals,
        }
    
    def delete_goal(self, goal_id: str) -> Dict:
        """Delete a goal and its log"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("DELETE FROM goal_log WHERE goal_id = ?", (goal_id,))
        conn.execute("DELETE FROM goals WHERE goal_id = ?", (goal_id,))
        conn.commit()
        conn.close()
        return {"ok": True, "deleted": goal_id}
