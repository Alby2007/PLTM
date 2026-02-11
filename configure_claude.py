#!/usr/bin/env python3
"""
PLTM Claude Desktop Configurator
=================================
Automatically generates and installs the Claude Desktop config for PLTM.

    python configure_claude.py

It will:
  1. Detect your OS and locate the Claude Desktop config file
  2. Generate the correct MCP server entry with absolute paths
  3. Merge it into your existing config (preserving other servers)
  4. Optionally read GROQ_API_KEY from .env
"""

import json
import os
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
IS_WIN = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"

VENV_PYTHON = str(
    ROOT / ".venv" / ("Scripts" if IS_WIN else "bin") / ("python.exe" if IS_WIN else "python3")
)


def get_config_path() -> Path:
    """Detect Claude Desktop config path based on OS."""
    if IS_WIN:
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
        return Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    elif IS_MAC:
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    else:  # Linux
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def read_groq_key() -> str:
    """Try to read GROQ_API_KEY from .env file."""
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("GROQ_API_KEY=") and not line.endswith("="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val and val != "your-groq-key" and not val.startswith("sk-ant-"):
                    return val
    # Also check environment
    return os.environ.get("GROQ_API_KEY", "")


def build_pltm_entry(groq_key: str) -> dict:
    """Build the MCP server config entry for PLTM."""
    env = {"PYTHONPATH": str(ROOT)}
    if groq_key:
        env["GROQ_API_KEY"] = groq_key
    
    return {
        "command": VENV_PYTHON,
        "args": ["-m", "mcp_server.pltm_server"],
        "env": env,
    }


def main():
    print("\n  PLTM — Claude Desktop Configurator\n")
    
    config_path = get_config_path()
    print(f"  Config path: {config_path}")
    print(f"  PLTM root:   {ROOT}")
    print(f"  Python:       {VENV_PYTHON}")
    
    # Check venv exists
    if not Path(VENV_PYTHON).exists():
        print(f"\n  ERROR: Virtual environment not found at {VENV_PYTHON}")
        print("  Run 'python setup_pltm.py' first.")
        sys.exit(1)
    
    # Read GROQ key
    groq_key = read_groq_key()
    if groq_key:
        print(f"  GROQ key:     ...{groq_key[-6:]}")
    else:
        print("  GROQ key:     not set (LLM tools will be unavailable)")
        print("  TIP: Add GROQ_API_KEY to .env (free at console.groq.com)")
    
    # Load existing config or create new
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            print(f"\n  Existing config found with {len(config.get('mcpServers', {}))} server(s)")
        except (json.JSONDecodeError, Exception) as e:
            print(f"\n  WARNING: Could not parse existing config: {e}")
            print("  Will create a new one.")
    
    # Merge PLTM entry
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    already_exists = "pltm" in config.get("mcpServers", {})
    config["mcpServers"]["pltm"] = build_pltm_entry(groq_key)
    
    # Write config
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2))
    
    action = "Updated" if already_exists else "Added"
    print(f"\n  {action} 'pltm' in {config_path}")
    print(f"\n  {'='*50}")
    print(f"  Done! Restart Claude Desktop to activate PLTM.")
    print(f"  You should see 136 tools available.")
    print(f"  {'='*50}\n")


if __name__ == "__main__":
    main()
