"""
Authenticated API Client

Makes HTTP requests with authentication, headers, and rate-limit tracking.
Supports Bearer tokens, API keys, Basic auth, and custom headers.
Tracks rate limits per domain.
"""

import base64
import json
import sqlite3
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class APIClient:
    """Authenticated HTTP client with rate-limit tracking."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).parent.parent.parent / "data" / "pltm_mcp.db"
        self.timeout = 15
        self._ensure_tables()
    
    def _ensure_tables(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_profiles (
                profile_id TEXT PRIMARY KEY,
                base_url TEXT NOT NULL,
                auth_type TEXT DEFAULT 'none',
                auth_value TEXT DEFAULT '',
                headers TEXT DEFAULT '{}',
                rate_limit_per_min INTEGER DEFAULT 60,
                requests_made INTEGER DEFAULT 0,
                last_request REAL,
                created_at REAL NOT NULL,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT,
                method TEXT,
                url TEXT,
                status_code INTEGER,
                response_size INTEGER,
                elapsed_ms INTEGER,
                timestamp REAL NOT NULL
            )
        """)
        conn.commit()
        conn.close()
    
    def create_profile(self, profile_id: str, base_url: str,
                       auth_type: str = "none", auth_value: str = "",
                       headers: Optional[Dict] = None,
                       rate_limit_per_min: int = 60) -> Dict:
        """
        Create an API profile for reuse.
        
        auth_type: 'none', 'bearer', 'api_key', 'basic', 'header'
        auth_value: token, key, user:pass, or header_name:value
        """
        now = time.time()
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT OR REPLACE INTO api_profiles (profile_id, base_url, auth_type, auth_value, headers, rate_limit_per_min, created_at) VALUES (?,?,?,?,?,?,?)",
            (profile_id, base_url, auth_type, auth_value,
             json.dumps(headers or {}), rate_limit_per_min, now)
        )
        conn.commit()
        conn.close()
        return {"ok": True, "profile_id": profile_id, "base_url": base_url, "auth_type": auth_type}
    
    def request(self, url: str = "", method: str = "GET",
                profile_id: Optional[str] = None,
                headers: Optional[Dict] = None,
                body: Optional[Any] = None,
                auth_type: Optional[str] = None,
                auth_value: Optional[str] = None,
                timeout: Optional[int] = None,
                params: Optional[Dict] = None) -> Dict:
        """
        Make an HTTP request with optional authentication.
        
        Can use a saved profile or inline auth.
        """
        start = time.time()
        req_headers = {"User-Agent": "PLTM/2.0"}
        base_url = ""
        
        # Load profile if specified
        if profile_id:
            profile = self._load_profile(profile_id)
            if not profile:
                return {"ok": False, "err": f"Profile '{profile_id}' not found"}
            
            base_url = profile["base_url"]
            auth_type = auth_type or profile["auth_type"]
            auth_value = auth_value or profile["auth_value"]
            
            profile_headers = json.loads(profile["headers"]) if isinstance(profile["headers"], str) else profile["headers"]
            req_headers.update(profile_headers)
            
            # Rate limit check
            if profile.get("rate_limit_per_min"):
                if not self._check_rate_limit(profile_id, profile["rate_limit_per_min"]):
                    return {"ok": False, "err": "Rate limit exceeded", "retry_after_seconds": 60}
        
        # Build full URL
        full_url = base_url.rstrip("/") + "/" + url.lstrip("/") if base_url else url
        
        # Add query params
        if params:
            separator = "&" if "?" in full_url else "?"
            full_url += separator + urllib.parse.urlencode(params)
        
        # Apply auth
        if auth_type == "bearer":
            req_headers["Authorization"] = f"Bearer {auth_value}"
        elif auth_type == "api_key":
            # Try as query param first, then header
            if "?" in full_url:
                full_url += f"&api_key={auth_value}"
            else:
                full_url += f"?api_key={auth_value}"
        elif auth_type == "basic":
            if ":" in (auth_value or ""):
                encoded = base64.b64encode(auth_value.encode()).decode()
                req_headers["Authorization"] = f"Basic {encoded}"
        elif auth_type == "header":
            if ":" in (auth_value or ""):
                h_name, h_val = auth_value.split(":", 1)
                req_headers[h_name.strip()] = h_val.strip()
        
        # Merge custom headers
        if headers:
            req_headers.update(headers)
        
        # Build request
        data = None
        if body is not None:
            if isinstance(body, dict):
                data = json.dumps(body).encode()
                req_headers.setdefault("Content-Type", "application/json")
            elif isinstance(body, str):
                data = body.encode()
            else:
                data = str(body).encode()
        
        try:
            req = urllib.request.Request(
                full_url,
                data=data,
                headers=req_headers,
                method=method.upper()
            )
            
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                response_data = resp.read()
                status_code = resp.status
                resp_headers = dict(resp.headers)
            
            elapsed_ms = int((time.time() - start) * 1000)
            
            # Try to parse as JSON
            try:
                parsed = json.loads(response_data)
                response_body = parsed
            except (json.JSONDecodeError, UnicodeDecodeError):
                response_body = response_data.decode("utf-8", errors="replace")[:5000]
            
            # Log request
            self._log_request(profile_id, method, full_url, status_code, len(response_data), elapsed_ms)
            
            result = {
                "ok": True,
                "status": status_code,
                "body": response_body,
                "size": len(response_data),
                "ms": elapsed_ms,
            }
            
            # Include rate limit headers if present
            for h in ["X-RateLimit-Remaining", "X-RateLimit-Limit", "Retry-After"]:
                if h in resp_headers:
                    result[h.lower().replace("-", "_")] = resp_headers[h]
            
            return result
            
        except urllib.error.HTTPError as e:
            elapsed_ms = int((time.time() - start) * 1000)
            self._log_request(profile_id, method, full_url, e.code, 0, elapsed_ms)
            
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:1000]
            except Exception:
                pass
            
            return {"ok": False, "status": e.code, "err": str(e.reason), "body": body, "ms": elapsed_ms}
            
        except Exception as e:
            return {"ok": False, "err": str(e)[:200]}
    
    def _load_profile(self, profile_id: str) -> Optional[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute("SELECT * FROM api_profiles WHERE profile_id = ?", (profile_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))
    
    def _check_rate_limit(self, profile_id: str, limit_per_min: int) -> bool:
        """Check if we're within rate limits"""
        conn = sqlite3.connect(str(self.db_path))
        one_min_ago = time.time() - 60
        cursor = conn.execute(
            "SELECT COUNT(*) FROM api_request_log WHERE profile_id = ? AND timestamp > ?",
            (profile_id, one_min_ago)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count < limit_per_min
    
    def _log_request(self, profile_id: Optional[str], method: str, url: str,
                     status: int, size: int, elapsed_ms: int):
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                "INSERT INTO api_request_log (profile_id, method, url, status_code, response_size, elapsed_ms, timestamp) VALUES (?,?,?,?,?,?,?)",
                (profile_id, method, url[:200], status, size, elapsed_ms, time.time())
            )
            # Update profile stats
            if profile_id:
                conn.execute(
                    "UPDATE api_profiles SET requests_made = requests_made + 1, last_request = ? WHERE profile_id = ?",
                    (time.time(), profile_id)
                )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to log API request: {e}")
    
    def list_profiles(self) -> Dict:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            "SELECT profile_id, base_url, auth_type, rate_limit_per_min, requests_made, last_request FROM api_profiles ORDER BY profile_id"
        )
        rows = cursor.fetchall()
        conn.close()
        return {
            "ok": True,
            "profiles": [
                {"id": r[0], "url": r[1], "auth": r[2], "rate_limit": r[3],
                 "requests": r[4], "last": r[5]}
                for r in rows
            ]
        }
    
    def delete_profile(self, profile_id: str) -> Dict:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("DELETE FROM api_profiles WHERE profile_id = ?", (profile_id,))
        conn.commit()
        conn.close()
        return {"ok": True, "deleted": profile_id}
