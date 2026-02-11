#!/usr/bin/env python3
"""
PLTM One-Command Setup
======================
Run this after cloning the repo:

    python setup_pltm.py

It will:
  1. Create a virtual environment (.venv)
  2. Install dependencies
  3. Create .env from template
  4. Initialize a clean database (if none exists)
  5. Pre-download the embedding model
"""

import subprocess
import sys
import os
import platform
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
VENV = ROOT / ".venv"
DATA = ROOT / "data"
DB_PATH = DATA / "pltm_mcp.db"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"

IS_WIN = platform.system() == "Windows"
PYTHON = VENV / ("Scripts" if IS_WIN else "bin") / ("python.exe" if IS_WIN else "python3")
PIP = VENV / ("Scripts" if IS_WIN else "bin") / ("pip.exe" if IS_WIN else "pip")


def header(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def run(cmd, **kwargs):
    print(f"  > {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"  ERROR: Command failed with exit code {result.returncode}")
        sys.exit(1)
    return result


def step_venv():
    header("Step 1/5 — Creating virtual environment")
    if VENV.exists():
        print(f"  .venv already exists at {VENV}, skipping.")
        return
    run([sys.executable, "-m", "venv", str(VENV)])
    print("  Created .venv")


def step_deps():
    header("Step 2/5 — Installing dependencies")
    # Upgrade pip first
    run([str(PIP), "install", "--upgrade", "pip", "-q"])
    
    req_file = ROOT / "requirements-lite.txt"
    if not req_file.exists():
        req_file = ROOT / "requirements.txt"
    
    run([str(PIP), "install", "-r", str(req_file)])
    print(f"  Installed from {req_file.name}")


def step_env():
    header("Step 3/5 — Setting up .env")
    if ENV_FILE.exists():
        print("  .env already exists, skipping.")
        return
    
    if ENV_EXAMPLE.exists():
        shutil.copy2(ENV_EXAMPLE, ENV_FILE)
        print("  Copied .env.example → .env")
    else:
        ENV_FILE.write_text(
            "# PLTM Configuration\n"
            "# Get a free key at https://console.groq.com\n"
            "GROQ_API_KEY=\n"
            "\n"
            "# Optional\n"
            "DEEPSEEK_API_KEY=\n"
            "LOG_LEVEL=INFO\n"
        )
        print("  Created .env template")
    
    print("  NOTE: Edit .env to add your GROQ_API_KEY (free at console.groq.com)")


def step_db():
    header("Step 4/5 — Initializing database")
    DATA.mkdir(parents=True, exist_ok=True)
    
    if DB_PATH.exists():
        print(f"  Database already exists at {DB_PATH}")
        # Show stats
        try:
            import sqlite3
            conn = sqlite3.connect(str(DB_PATH))
            tables = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            print(f"  {tables} tables found")
            conn.close()
        except Exception:
            pass
        return
    
    # Create a fresh DB by running the server init briefly
    print("  Creating fresh database...")
    init_script = (
        "import asyncio, sys; sys.path.insert(0, r'" + str(ROOT) + "'); "
        "from mcp_server.pltm_server import initialize_pltm; "
        "asyncio.run(initialize_pltm())"
    )
    run([str(PYTHON), "-c", init_script], cwd=str(ROOT))
    print(f"  Database created at {DB_PATH}")


def step_model():
    header("Step 5/5 — Pre-downloading embedding model")
    dl_script = (
        "try:\n"
        "    from sentence_transformers import SentenceTransformer\n"
        "    m = SentenceTransformer('all-MiniLM-L6-v2')\n"
        "    print('  Model ready: all-MiniLM-L6-v2 (384-dim)')\n"
        "except ImportError:\n"
        "    print('  sentence-transformers not installed, skipping model download.')\n"
        "    print('  Embedding search will be unavailable. Install with:')\n"
        "    print('    pip install sentence-transformers')\n"
    )
    run([str(PYTHON), "-c", dl_script], cwd=str(ROOT))


def done():
    python_rel = ".venv\\Scripts\\python.exe" if IS_WIN else ".venv/bin/python3"
    
    print(f"\n{'='*60}")
    print("  PLTM setup complete!")
    print(f"{'='*60}")
    print()
    print("  Next steps:")
    print()
    print("  1. Add your API key:")
    print(f"     Edit .env and set GROQ_API_KEY (free at console.groq.com)")
    print()
    print("  2. Configure Claude Desktop:")
    print(f"     python configure_claude.py")
    print()
    print("  3. Restart Claude Desktop — 136 tools will be available!")
    print()
    print("  Optional — run health check:")
    print(f"     {python_rel} health_check.py")
    print()


if __name__ == "__main__":
    print("\n  PLTM — Persistent Long-Term Memory for Claude")
    print("  One-command setup\n")
    
    step_venv()
    step_deps()
    step_env()
    step_db()
    step_model()
    done()
