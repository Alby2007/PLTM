"""
Task Scheduler

Persistent task scheduling with cron-like expressions.
Tasks are stored in SQLite and can be checked/executed across conversations.
Since MCP can't run daemons, this stores task definitions that Claude
checks on conversation start via check_scheduled_tasks.
"""

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class TaskScheduler:
    """Schedule and track recurring tasks."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).parent.parent.parent / "data" / "pltm_mcp.db"
        self._ensure_tables()
    
    def _ensure_tables(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                task_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                task_type TEXT NOT NULL,
                schedule TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                last_run REAL,
                next_due REAL,
                run_count INTEGER DEFAULT 0,
                max_runs INTEGER,
                tool_name TEXT,
                tool_args TEXT DEFAULT '{}',
                script_path TEXT,
                created_at REAL NOT NULL,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS task_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                status TEXT NOT NULL,
                result TEXT DEFAULT '',
                started_at REAL NOT NULL,
                completed_at REAL,
                FOREIGN KEY (task_id) REFERENCES scheduled_tasks(task_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_task_status ON scheduled_tasks(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_task_due ON scheduled_tasks(next_due)")
        conn.commit()
        conn.close()
    
    def _schedule_to_seconds(self, schedule: str) -> float:
        """Convert schedule string to seconds interval"""
        schedules = {
            "hourly": 3600,
            "every_6h": 21600,
            "every_12h": 43200,
            "daily": 86400,
            "every_2d": 172800,
            "every_3d": 259200,
            "weekly": 604800,
            "biweekly": 1209600,
            "monthly": 2592000,
        }
        return schedules.get(schedule.lower(), 86400)  # Default daily
    
    def schedule_task(self, name: str, description: str, task_type: str,
                      schedule: str = "daily", tool_name: Optional[str] = None,
                      tool_args: Optional[Dict] = None, script_path: Optional[str] = None,
                      max_runs: Optional[int] = None,
                      metadata: Optional[Dict] = None) -> Dict:
        """
        Schedule a recurring task.
        
        task_type: 'tool_call' (call an MCP tool), 'script' (run a script), 
                   'reminder' (just remind Claude to do something)
        schedule: 'hourly', 'every_6h', 'daily', 'weekly', 'monthly'
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        now = time.time()
        interval = self._schedule_to_seconds(schedule)
        next_due = now + interval
        
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            """INSERT INTO scheduled_tasks (task_id, name, description, task_type, schedule,
               status, last_run, next_due, run_count, max_runs, tool_name, tool_args,
               script_path, created_at, metadata)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (task_id, name, description, task_type, schedule,
             "active", None, next_due, 0, max_runs, tool_name,
             json.dumps(tool_args or {}), script_path, now,
             json.dumps(metadata or {}))
        )
        conn.commit()
        conn.close()
        
        return {"ok": True, "task_id": task_id, "name": name, "schedule": schedule,
                "next_due": next_due, "type": task_type}
    
    def check_due_tasks(self) -> Dict:
        """Check for tasks that are due. Call this at conversation start."""
        now = time.time()
        conn = sqlite3.connect(str(self.db_path))
        
        # Get overdue tasks
        cursor = conn.execute(
            "SELECT task_id, name, description, task_type, schedule, tool_name, tool_args, script_path, next_due, run_count, max_runs FROM scheduled_tasks WHERE status = 'active' AND next_due <= ? ORDER BY next_due ASC",
            (now,)
        )
        due = cursor.fetchall()
        
        # Get all active tasks for summary
        cursor = conn.execute(
            "SELECT task_id, name, schedule, next_due, run_count FROM scheduled_tasks WHERE status = 'active' ORDER BY next_due ASC"
        )
        all_active = cursor.fetchall()
        conn.close()
        
        due_tasks = []
        for t in due:
            overdue_hours = (now - t[8]) / 3600
            task = {
                "task_id": t[0], "name": t[1], "description": t[2],
                "type": t[3], "schedule": t[4],
                "overdue_hours": round(overdue_hours, 1),
                "run_count": t[9],
            }
            if t[5]:  # tool_name
                task["tool_name"] = t[5]
                task["tool_args"] = json.loads(t[6]) if t[6] else {}
            if t[7]:  # script_path
                task["script_path"] = t[7]
            due_tasks.append(task)
        
        upcoming = [{"id": t[0], "name": t[1], "schedule": t[2],
                     "due_in_hours": round((t[3] - now) / 3600, 1),
                     "runs": t[4]} for t in all_active if t[3] > now]
        
        return {
            "ok": True,
            "due_count": len(due_tasks),
            "due_tasks": due_tasks,
            "upcoming": upcoming[:10],
            "total_active": len(all_active),
        }
    
    def mark_task_run(self, task_id: str, result: str = "", status: str = "success") -> Dict:
        """Mark a task as having been run. Advances next_due."""
        now = time.time()
        conn = sqlite3.connect(str(self.db_path))
        
        cursor = conn.execute(
            "SELECT schedule, run_count, max_runs FROM scheduled_tasks WHERE task_id = ?",
            (task_id,)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"ok": False, "err": f"Task '{task_id}' not found"}
        
        schedule, run_count, max_runs = row
        new_count = run_count + 1
        interval = self._schedule_to_seconds(schedule)
        next_due = now + interval
        
        # Check if max runs reached
        new_status = "active"
        if max_runs and new_count >= max_runs:
            new_status = "completed"
        
        conn.execute(
            "UPDATE scheduled_tasks SET last_run = ?, next_due = ?, run_count = ?, status = ? WHERE task_id = ?",
            (now, next_due, new_count, new_status, task_id)
        )
        conn.execute(
            "INSERT INTO task_runs (task_id, status, result, started_at, completed_at) VALUES (?,?,?,?,?)",
            (task_id, status, result[:500], now, now)
        )
        conn.commit()
        conn.close()
        
        return {"ok": True, "task_id": task_id, "run_count": new_count,
                "next_due": next_due if new_status == "active" else None,
                "status": new_status}
    
    def pause_task(self, task_id: str) -> Dict:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("UPDATE scheduled_tasks SET status = 'paused' WHERE task_id = ?", (task_id,))
        conn.commit()
        conn.close()
        return {"ok": True, "task_id": task_id, "status": "paused"}
    
    def resume_task(self, task_id: str) -> Dict:
        now = time.time()
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute("SELECT schedule FROM scheduled_tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"ok": False, "err": "Task not found"}
        interval = self._schedule_to_seconds(row[0])
        conn.execute(
            "UPDATE scheduled_tasks SET status = 'active', next_due = ? WHERE task_id = ?",
            (now + interval, task_id)
        )
        conn.commit()
        conn.close()
        return {"ok": True, "task_id": task_id, "status": "active"}
    
    def delete_task(self, task_id: str) -> Dict:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("DELETE FROM task_runs WHERE task_id = ?", (task_id,))
        conn.execute("DELETE FROM scheduled_tasks WHERE task_id = ?", (task_id,))
        conn.commit()
        conn.close()
        return {"ok": True, "deleted": task_id}
    
    def get_task_history(self, task_id: str, limit: int = 20) -> List[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            "SELECT status, result, started_at, completed_at FROM task_runs WHERE task_id = ? ORDER BY started_at DESC LIMIT ?",
            (task_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        return [{"status": r[0], "result": r[1][:100], "started": r[2], "completed": r[3]} for r in rows]
