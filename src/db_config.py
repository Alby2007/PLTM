"""
Centralized DB path configuration.

All modules should import DB_PATH from here instead of hardcoding.
Call set_db_path() before initialization to use a different database
(e.g., separate Ollama graph from Claude's graph).
"""
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "pltm_mcp.db"


def set_db_path(path: str):
    """Override DB path globally (e.g., for Ollama's separate memory graph)."""
    global DB_PATH
    DB_PATH = Path(path)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_db_path() -> Path:
    """Get the current DB path."""
    return DB_PATH
