"""
DreamByte Studios - MCP Server

Exposes the animation engine as tools that any MCP-compatible AI agent can call
(Claude Desktop, Cursor, Windsurf, Cline, etc.).

Run with:
    python mcp_server.py

Configure in Claude Desktop / Cursor mcp.json:
{
  "mcpServers": {
    "dreambyte": {
      "command": "python",
      "args": ["/absolute/path/to/DreamByte-Studios/backend/mcp_server.py"],
      "env": { "DREAMBYTE_API": "http://127.0.0.1:8000" }
    }
  }
}
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("mcp package not installed. Run: pip install mcp")
    FastMCP = None

if FastMCP:
    mcp = FastMCP("DreamByte Studios Animation Engine")
else:
    mcp = None

def _api_base() -> str:
    import os
    return os.environ.get("DREAMBYTE_API", "http://127.0.0.1:8000")

if mcp:

    @mcp.tool()
    def list_models() -> str:
        """List all 3D models currently uploaded to DreamByte Studios."""
        import urllib.request
        try:
            with urllib.request.urlopen(f"{_api_base()}/api/files") as r:
                data = json.loads(r.read().decode())
            if not data:
                return "No models uploaded yet. Use the editor or /api/upload first."
            lines = [f"- {f['filename']} ({f['size']} bytes)" for f in data]
            return "Uploaded models:\n" + "\n".join(lines)
        except Exception as e:
            return f"Error talking to DreamByte API: {e}. Is the backend running on {_api_base()}?"

    @mcp.tool()
    def get_animation_prompt(filename: str, motion_description: str) -> str:
        """Build a complete prompt so an LLM can generate a Blender Python script for the given model."""
        import urllib.request
        payload = json.dumps({"filename": filename, "message": motion_description}).encode()
        req = urllib.request.Request(
            f"{_api_base()}/api/prompt",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read().decode())
            return data.get("prompt", str(data))
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool()
    def run_animation_script(code: str, filename: str = "") -> str:
        """Execute a bpy script that animates the model and overwrites the file."""
        import urllib.request
        payload = json.dumps({"code": code, "filename": filename or None}).encode()
        req = urllib.request.Request(
            f"{_api_base()}/api/run",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read().decode())
            if data.get("ok"):
                return f"Success!\noutput: {data.get('output_url')}\nstdout: {data.get('stdout', '')[:500]}"
            return f"Script failed (code {data.get('returncode')})\nstderr: {data.get('stderr', '')[:800]}"
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool()
    def animate_model(filename: str, motion_description: str) -> str:
        """High-level helper: returns the prompt. Agent should then call an LLM and finally run_animation_script."""
        prompt = get_animation_prompt(filename, motion_description)
        return (
            "Here is the complete prompt to send to any LLM:\n\n"
            "----- PROMPT START -----\n"
            f"{prompt}\n"
            "----- PROMPT END -----\n\n"
            "After the LLM returns the Python code, call run_animation_script with that code."
        )

if __name__ == "__main__":
    if mcp is None:
        print("Install the official MCP SDK first: pip install mcp")
        sys.exit(1)
    print("Starting DreamByte MCP server (stdio)...")
    mcp.run(transport="stdio")
