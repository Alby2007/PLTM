"""
Patch pltm-mcp/server.py with three fixes:
  1. Write verification in handle_store_atom
  2. Timeout wrapper (30s) + store-null guard on call_tool
  3. Re-indent elif chain for new _dispatch_tool function

Uses line-by-line matching to tolerate trailing whitespace.
"""
import py_compile

SERVER_PATH = r"C:\Users\alber\CascadeProjects\pltm-mcp\server.py"

with open(SERVER_PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

patches_applied = 0


def find_line(lines, needle, start=0):
    """Find line index containing needle (stripped), starting from start."""
    for i in range(start, len(lines)):
        if needle in lines[i].rstrip():
            return i
    return -1


# ============================================================
# PATCH 1: Write verification in handle_store_atom
# Find:  "    # Store in database" ... "    )]"
# ============================================================
p1_start = find_line(lines, "# Store in database")
if p1_start >= 0:
    # Find the closing ")]" of the return statement
    p1_end = -1
    for i in range(p1_start, min(len(lines), p1_start + 20)):
        if lines[i].strip() == ")]":
            p1_end = i
            break

    if p1_end >= 0:
        new_block = [
            "    # Store in database\n",
            "    await store.add_atom(atom)\n",
            "\n",
            "    # Verify write succeeded\n",
            "    verified = False\n",
            "    try:\n",
            "        check = await store.get_atom(atom.id)\n",
            "        verified = check is not None\n",
            "    except Exception:\n",
            "        verified = False\n",
            "\n",
            "    if not verified:\n",
            "        logger.error(f\"WRITE VERIFICATION FAILED for atom {atom.id}\")\n",
            "\n",
            "    return [TextContent(\n",
            "        type=\"text\",\n",
            "        text=compact_json({\n",
            "            \"status\": \"stored\" if verified else \"WRITE_FAILED\",\n",
            "            \"atom_id\": str(atom.id),\n",
            "            \"verified\": verified,\n",
            "            \"atom_type\": args[\"atom_type\"],\n",
            "            \"content\": f\"{args['subject']} {args['predicate']} {args['object']}\"\n",
            "        })\n",
            "    )]\n",
        ]
        lines[p1_start:p1_end + 1] = new_block
        patches_applied += 1
        print(f"PATCH 1 (write verification): APPLIED (replaced lines {p1_start+1}-{p1_end+1})")
    else:
        print("PATCH 1: Could not find closing ')]'")
else:
    print("PATCH 1: Could not find '# Store in database'")


# ============================================================
# PATCH 2: Timeout wrapper + store guard
# Replace @app.call_tool() block header with _dispatch_tool
# ============================================================
p2_start = find_line(lines, "@app.call_tool()")
if p2_start >= 0:
    # Find the "try:" and first "if name ==" lines
    try_line = find_line(lines, "try:", p2_start)
    first_if = find_line(lines, 'if name == "store_memory_atom":', p2_start)

    if try_line >= 0 and first_if >= 0:
        # Replace from @app.call_tool() through the first if statement
        new_header = [
            "async def _dispatch_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:\n",
            "    \"\"\"Inner dispatch for tool calls (wrapped by call_tool with timeout).\"\"\"\n",
            "    if name == \"store_memory_atom\":\n",
            "        return await handle_store_atom(arguments)\n",
        ]
        lines[p2_start:first_if + 2] = new_header
        patches_applied += 1
        print(f"PATCH 2a (extract _dispatch_tool): APPLIED")
    else:
        print("PATCH 2a: Could not find try/if structure")
else:
    print("PATCH 2a: Could not find @app.call_tool()")


# Find and replace the except block at the end of the dispatch
p2b_except = find_line(lines, "except Exception as e:")
if p2b_except >= 0:
    # Check this is the right except (should be after the else/Unknown tool block)
    # Find the closing ")]" of the except block
    p2b_end = -1
    for i in range(p2b_except, min(len(lines), p2b_except + 10)):
        if lines[i].strip() == ")]":
            p2b_end = i
            break

    # Also find the "else:" + "Unknown tool" block just before except
    else_line = -1
    for i in range(p2b_except - 6, p2b_except):
        if "else:" in lines[i] and i >= 0:
            else_line = i
            break

    if p2b_end >= 0 and else_line >= 0:
        new_tail = [
            "    else:\n",
            "        return [TextContent(\n",
            "            type=\"text\",\n",
            "            text=f\"Unknown tool: {name}\"\n",
            "        )]\n",
            "\n",
            "\n",
            "@app.call_tool()\n",
            "async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:\n",
            "    \"\"\"Handle tool calls with timeout and store guard.\"\"\"\n",
            "    if store is None:\n",
            "        return [TextContent(\n",
            "            type=\"text\",\n",
            "            text=\"Error: PLTM not initialized. Restart the MCP server.\"\n",
            "        )]\n",
            "\n",
            "    try:\n",
            "        result = await asyncio.wait_for(_dispatch_tool(name, arguments), timeout=30.0)\n",
            "        return result\n",
            "    except asyncio.TimeoutError:\n",
            "        logger.error(f\"Tool {name} timed out after 30s\")\n",
            "        return [TextContent(\n",
            "            type=\"text\",\n",
            "            text=f\"Error: Tool '{name}' timed out after 30s\"\n",
            "        )]\n",
            "    except Exception as e:\n",
            "        logger.error(f\"Error in tool {name}: {e}\")\n",
            "        return [TextContent(\n",
            "            type=\"text\",\n",
            "            text=f\"Error: {str(e)}\"\n",
            "        )]\n",
        ]
        lines[else_line:p2b_end + 1] = new_tail
        patches_applied += 1
        print(f"PATCH 2b (timeout wrapper): APPLIED")
    else:
        print(f"PATCH 2b: Could not find else/except boundaries (else={else_line}, end={p2b_end})")
else:
    print("PATCH 2b: Could not find 'except Exception'")


# ============================================================
# PATCH 3: Fix indentation of elif chain (8-space -> 4-space)
# inside _dispatch_tool
# ============================================================
in_dispatch = False
indent_fixes = 0

for i in range(len(lines)):
    if "async def _dispatch_tool" in lines[i]:
        in_dispatch = True
        continue

    if in_dispatch:
        stripped = lines[i].lstrip()
        # Stop at next top-level definition
        if (stripped.startswith("@app.") or
            stripped.startswith("@") and "def " in stripped or
            (not lines[i].startswith(" ") and not lines[i].startswith("\n") and
             ("async def " in lines[i] or "def " in lines[i]))):
            in_dispatch = False
            continue

        # Fix 8-space elif to 4-space
        if lines[i].startswith("        elif "):
            lines[i] = "    elif " + lines[i][13:]
            indent_fixes += 1
        elif lines[i].startswith("            return "):
            lines[i] = "        return " + lines[i][19:]
            indent_fixes += 1
        elif lines[i].startswith("        # ") and not lines[i].startswith("        # Verify"):
            lines[i] = "    # " + lines[i][10:]
            indent_fixes += 1

if indent_fixes > 0:
    patches_applied += 1
    print(f"PATCH 3 (indent fix): APPLIED ({indent_fixes} lines fixed)")
else:
    print("PATCH 3 (indent fix): no fixes needed")


# ============================================================
# Write result
# ============================================================
if patches_applied > 0:
    with open(SERVER_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"\nDone: {patches_applied} patches applied to {SERVER_PATH}")
else:
    print("\nNo patches applied. File unchanged.")

# Verify syntax
try:
    py_compile.compile(SERVER_PATH, doraise=True)
    print("Syntax check: OK")
except py_compile.PyCompileError as e:
    print(f"Syntax check: FAILED - {e}")
