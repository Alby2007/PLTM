"""
Ollama Chat Client with PLTM Tool Calling

Local AI assistant that connects Ollama (qwen3:8b) directly to your PLTM tools.
Runs entirely locally — no API keys, no usage limits.

Usage:
    python ollama_chat.py
"""

import asyncio
import json
import sys
import httpx
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.db_config import set_db_path
from mcp_server.pltm_server import (
    initialize_pltm, _dispatch_tool, list_tools
)

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen3:8b"
USER_ID = "alby"

# Separate DB for Ollama — keeps Claude's memory graph untouched
OLLAMA_DB_PATH = str(Path(__file__).parent / "data" / "pltm_ollama.db")

# System prompt for the local assistant
SYSTEM_PROMPT = """You are a local AI assistant with access to PLTM (Procedural Long-Term Memory) tools.
You have persistent memory about the user and can store/retrieve personality traits, facts, preferences, and mood data.

Key behaviors:
- Use tools proactively to store observations about the user
- Check personality data when asked about the user
- Track your own accuracy with epistemic tools
- Be direct and concise — the user prefers action over explanation

Available tool categories:
- Memory: store_memory_atom, query_personality, get_personality_summary
- Mood: detect_mood, get_mood_patterns
- Personality: extract_personality_traits, bootstrap_from_sample, bootstrap_from_messages
- Claude Identity: init_claude_session, get_claude_personality, evolve_claude_personality
- Learning: learn_from_interaction, learn_from_url, learn_from_paper, learn_from_code
- Epistemic: check_before_claiming, log_claim, resolve_claim, get_calibration
- Session: predict_session, check_pltm_available, pltm_mode
- Analysis: deep_personality_analysis, domain_cognitive_map
- Data: query_pltm_sql

When starting a conversation, call check_pltm_available to see if user data exists."""


def mcp_tools_to_ollama_tools(mcp_tool_list):
    """Convert MCP Tool objects to Ollama tool format."""
    ollama_tools = []
    for tool in mcp_tool_list:
        ollama_tool = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        }
        ollama_tools.append(ollama_tool)
    return ollama_tools


async def call_ollama(messages, tools):
    """Call Ollama chat API with tool support."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {
            "model": MODEL,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_ctx": 8192,
            }
        }
        resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()


async def handle_tool_calls(tool_calls):
    """Execute PLTM tool calls and return results."""
    results = []
    for tc in tool_calls:
        name = tc["function"]["name"]
        args = tc["function"].get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}

        print(f"  \033[36m⚡ {name}\033[0m({json.dumps(args, separators=(',', ':'))[:80]})")

        try:
            text_contents = await _dispatch_tool(name, args)
            result_text = "\n".join(tc.text for tc in text_contents)
        except Exception as e:
            result_text = json.dumps({"error": str(e)})

        results.append({
            "role": "tool",
            "content": result_text,
        })
    return results


async def chat_loop():
    """Main interactive chat loop."""
    # Initialize PLTM
    print("\033[33m⏳ Initializing PLTM...\033[0m")
    print(f"  Ollama DB: {OLLAMA_DB_PATH}")
    print(f"  (Claude's DB at data/pltm_mcp.db is untouched)")
    # Set centralized DB path BEFORE any module initialization
    set_db_path(OLLAMA_DB_PATH)
    await initialize_pltm(custom_db_path=OLLAMA_DB_PATH)
    print("\033[32m✓ PLTM initialized (separate Ollama graph)\033[0m")

    # Get tools
    mcp_tool_list = await list_tools()
    ollama_tools = mcp_tools_to_ollama_tools(mcp_tool_list)
    print(f"\033[32m✓ {len(ollama_tools)} tools loaded\033[0m")

    # Check Ollama is running
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            models = [m["name"] for m in resp.json().get("models", [])]
            if not any(MODEL in m for m in models):
                print(f"\033[31m✗ Model {MODEL} not found. Available: {models}\033[0m")
                return
            print(f"\033[32m✓ Ollama running, model: {MODEL}\033[0m")
    except Exception as e:
        print(f"\033[31m✗ Ollama not running: {e}\033[0m")
        print("  Start it with: ollama serve")
        return

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print(f"\n\033[1m{'='*60}\033[0m")
    print(f"\033[1m  PLTM Local Chat — {MODEL}\033[0m")
    print(f"\033[1m  {len(ollama_tools)} tools available | User: {USER_ID}\033[0m")
    print(f"\033[1m  Type 'quit' to exit, 'tools' to list tools\033[0m")
    print(f"\033[1m{'='*60}\033[0m\n")

    while True:
        try:
            user_input = input("\033[1;37mYou: \033[0m").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\033[33mGoodbye!\033[0m")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("\033[33mGoodbye!\033[0m")
            break
        if user_input.lower() == "tools":
            for t in mcp_tool_list:
                print(f"  \033[36m{t.name}\033[0m — {t.description[:70]}")
            continue

        messages.append({"role": "user", "content": user_input})

        # Call Ollama — may need multiple rounds for tool calls
        max_rounds = 5
        for round_num in range(max_rounds):
            try:
                response = await call_ollama(messages, ollama_tools)
            except httpx.HTTPStatusError as e:
                print(f"\033[31mOllama error: {e}\033[0m")
                break
            except httpx.ConnectError:
                print("\033[31mCan't connect to Ollama. Is it running?\033[0m")
                break

            msg = response.get("message", {})
            tool_calls = msg.get("tool_calls", [])

            if tool_calls:
                # Add assistant message with tool calls
                messages.append(msg)

                # Execute tools
                tool_results = await handle_tool_calls(tool_calls)
                messages.extend(tool_results)
                # Continue loop for model to process tool results
            else:
                # Final text response
                content = msg.get("content", "")
                if content:
                    print(f"\n\033[1;32mAssistant:\033[0m {content}\n")
                messages.append({"role": "assistant", "content": content})
                break
        else:
            print("\033[33m(max tool rounds reached)\033[0m")


if __name__ == "__main__":
    print("\033[1;35m")
    print("  ╔══════════════════════════════════════╗")
    print("  ║   PLTM × Ollama Local Assistant      ║")
    print("  ║   Persistent Memory + Tool Calling   ║")
    print("  ╚══════════════════════════════════════╝")
    print("\033[0m")
    asyncio.run(chat_loop())
