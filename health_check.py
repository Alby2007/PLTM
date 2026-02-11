#!/usr/bin/env python3
"""
PLTM Health Check
=================
Verify that everything is set up correctly:

    python health_check.py
    # or: .venv/bin/python health_check.py
"""

import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
WARN = "\033[93m!\033[0m"

results = {"pass": 0, "fail": 0, "warn": 0}


def check(label, ok, warn_only=False):
    if ok:
        print(f"  {PASS} {label}")
        results["pass"] += 1
    elif warn_only:
        print(f"  {WARN} {label}")
        results["warn"] += 1
    else:
        print(f"  {FAIL} {label}")
        results["fail"] += 1
    return ok


def main():
    print("\n  PLTM Health Check\n")

    # 1. Python version
    v = sys.version_info
    check(f"Python {v.major}.{v.minor}.{v.micro}", v >= (3, 10))

    # 2. Core dependencies
    print()
    deps = {
        "mcp": "mcp",
        "aiosqlite": "aiosqlite",
        "loguru": "loguru",
        "numpy": "numpy",
    }
    for name, mod in deps.items():
        try:
            __import__(mod)
            check(f"{name} installed", True)
        except ImportError:
            check(f"{name} installed — run: pip install {name}", False)

    # 3. Optional deps
    try:
        __import__("sentence_transformers")
        check("sentence-transformers installed (embedding search)", True)
    except ImportError:
        check("sentence-transformers not installed (embedding search unavailable)", False, warn_only=True)

    try:
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer("all-MiniLM-L6-v2")
        check("Embedding model cached (all-MiniLM-L6-v2)", True)
    except Exception:
        check("Embedding model not cached — will download on first use", False, warn_only=True)

    # 4. Database
    print()
    db_path = ROOT / "data" / "pltm_mcp.db"
    check(f"Database exists at data/pltm_mcp.db", db_path.exists())

    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            tables = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            check(f"Database has {tables} tables", tables > 5)

            try:
                atoms = conn.execute("SELECT COUNT(*) FROM atoms").fetchone()[0]
                check(f"Knowledge atoms: {atoms}", True)
            except Exception:
                check("atoms table missing (will be created on first run)", False, warn_only=True)

            try:
                typed = conn.execute("SELECT COUNT(*) FROM typed_memories").fetchone()[0]
                check(f"Typed memories: {typed}", True)
            except Exception:
                check("typed_memories table missing (will be created on first run)", False, warn_only=True)

            conn.close()
        except Exception as e:
            check(f"Database readable: {e}", False)

    # 5. MCP server importable
    print()
    try:
        from mcp_server import pltm_server
        check("MCP server module importable", True)
    except Exception as e:
        check(f"MCP server import failed: {e}", False)

    # 6. .env / API keys
    print()
    env_file = ROOT / ".env"
    check(".env file exists", env_file.exists(), warn_only=True)

    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key and env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip().startswith("GROQ_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val and val != "your-groq-key":
                    groq_key = val
    if groq_key:
        check(f"GROQ_API_KEY set (...{groq_key[-6:]})", True)
    else:
        check("GROQ_API_KEY not set (LLM tools unavailable — free at console.groq.com)", False, warn_only=True)

    # 7. Claude Desktop config
    print()
    import platform
    if platform.system() == "Windows":
        appdata = os.environ.get("APPDATA", "")
        cfg = Path(appdata) / "Claude" / "claude_desktop_config.json" if appdata else None
    elif platform.system() == "Darwin":
        cfg = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    else:
        cfg = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    if cfg and cfg.exists():
        try:
            import json
            data = json.loads(cfg.read_text())
            has_pltm = "pltm" in data.get("mcpServers", {})
            check(f"Claude Desktop config has 'pltm' entry", has_pltm)
            if not has_pltm:
                print(f"    Run: python configure_claude.py")
        except Exception as e:
            check(f"Claude Desktop config readable: {e}", False)
    else:
        check("Claude Desktop config not found — run: python configure_claude.py", False, warn_only=True)

    # Summary
    total = results["pass"] + results["fail"] + results["warn"]
    print(f"\n  {'='*50}")
    print(f"  Results: {results['pass']}/{total} passed", end="")
    if results["warn"]:
        print(f", {results['warn']} warnings", end="")
    if results["fail"]:
        print(f", {results['fail']} failed", end="")
    print()

    if results["fail"] == 0:
        print("  PLTM is ready to use!")
    else:
        print("  Fix the failures above, then re-run this check.")
    print(f"  {'='*50}\n")

    sys.exit(0 if results["fail"] == 0 else 1)


if __name__ == "__main__":
    main()
