"""
System Context Provider

Returns system information: time, resources, environment, user context.
Enables context-aware behavior.
"""

import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger


class SystemContext:
    """Gather system context information."""
    
    def get_context(self) -> Dict:
        """Get full system context"""
        return {
            "time": self._get_time_context(),
            "system": self._get_system_info(),
            "resources": self._get_resources(),
            "environment": self._get_env_context(),
            "pltm": self._get_pltm_context(),
        }
    
    def _get_time_context(self) -> Dict:
        now = datetime.now()
        utc_now = datetime.now(timezone.utc)
        return {
            "local": now.isoformat(),
            "utc": utc_now.isoformat(),
            "timezone": time.tzname[0],
            "utc_offset_hours": -time.timezone / 3600,
            "day_of_week": now.strftime("%A"),
            "hour": now.hour,
            "is_business_hours": 9 <= now.hour <= 17,
            "unix_timestamp": time.time(),
        }
    
    def _get_system_info(self) -> Dict:
        return {
            "os": platform.system(),
            "os_version": platform.version()[:50],
            "machine": platform.machine(),
            "python": platform.python_version(),
            "hostname": platform.node(),
        }
    
    def _get_resources(self) -> Dict:
        """Get system resource usage"""
        resources = {}
        
        try:
            import psutil
            resources["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            resources["memory"] = {
                "total_gb": round(mem.total / (1024**3), 1),
                "used_gb": round(mem.used / (1024**3), 1),
                "percent": mem.percent,
            }
            disk = psutil.disk_usage("/")
            resources["disk"] = {
                "total_gb": round(disk.total / (1024**3), 1),
                "used_gb": round(disk.used / (1024**3), 1),
                "percent": round(disk.percent, 1),
            }
        except ImportError:
            # Fallback without psutil
            try:
                load = os.getloadavg()
                resources["load_avg"] = [round(l, 2) for l in load]
            except (OSError, AttributeError):
                pass
            
            # Try to get disk info from os
            try:
                st = os.statvfs("/")
                total = st.f_blocks * st.f_frsize
                free = st.f_bavail * st.f_frsize
                resources["disk"] = {
                    "total_gb": round(total / (1024**3), 1),
                    "free_gb": round(free / (1024**3), 1),
                }
            except (OSError, AttributeError):
                pass
        
        return resources
    
    def _get_env_context(self) -> Dict:
        """Get relevant environment variables (non-sensitive)"""
        safe_vars = ["HOME", "USER", "SHELL", "LANG", "TERM", "PATH"]
        env = {}
        for var in safe_vars:
            val = os.environ.get(var)
            if val:
                if var == "PATH":
                    env[var] = f"{len(val.split(':'))} entries"
                else:
                    env[var] = val
        return env
    
    def _get_pltm_context(self) -> Dict:
        """Get PLTM-specific context"""
        import sqlite3
        db_path = Path(__file__).parent.parent.parent / "data" / "pltm_mcp.db"
        
        context = {"db_exists": db_path.exists()}
        
        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path))
                
                # Atom count
                cursor = conn.execute("SELECT COUNT(*) FROM atoms")
                context["total_atoms"] = cursor.fetchone()[0]
                
                # Recent activity
                cursor = conn.execute("SELECT MAX(first_observed) FROM atoms")
                row = cursor.fetchone()
                if row[0]:
                    context["last_atom_stored"] = row[0]
                
                # Goal count
                try:
                    cursor = conn.execute("SELECT status, COUNT(*) FROM goals GROUP BY status")
                    context["goals"] = {r[0]: r[1] for r in cursor.fetchall()}
                except Exception:
                    pass
                
                # Scheduled tasks
                try:
                    cursor = conn.execute("SELECT COUNT(*) FROM scheduled_tasks WHERE status = 'active'")
                    context["active_tasks"] = cursor.fetchone()[0]
                except Exception:
                    pass
                
                # Indicators
                try:
                    cursor = conn.execute("SELECT COUNT(*) FROM indicators WHERE status = 'breached'")
                    context["breached_indicators"] = cursor.fetchone()[0]
                except Exception:
                    pass
                
                # Due tasks
                try:
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM scheduled_tasks WHERE status = 'active' AND next_due <= ?",
                        (time.time(),)
                    )
                    context["due_tasks"] = cursor.fetchone()[0]
                except Exception:
                    pass
                
                conn.close()
            except Exception as e:
                context["db_error"] = str(e)[:50]
        
        context["db_size_mb"] = round(db_path.stat().st_size / (1024*1024), 2) if db_path.exists() else 0
        
        return context
