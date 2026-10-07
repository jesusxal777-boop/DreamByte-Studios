# DreamByte Studios

**Animation Engine for AIs — Zero Cost • Unrestricted • Local-First • MCP Native**

> Turn any rigged 3D model (OBJ, GLB, FBX) into a fully animated character using natural language.  
> Built for AI agents. Powered by **DreamBot**.

## Features

- Text-to-Animation for rigged 3D models
- Supports OBJ / GLB / GLTF / FBX
- **MCP native** (Claude, Cursor, Windsurf…)
- Liquid Glass UI + full Editor
- Completely free & local
- One AI inference per animation
- Live Three.js preview

## Quick Start

```bash
git clone https://github.com/jesusxal777-boop/DreamByte-Studios.git
cd DreamByte-Studios/backend
pip install -r requirements.txt
python main.py
# → http://127.0.0.1:8000
```

- Landing: http://127.0.0.1:8000/public/index.html
- Editor:  http://127.0.0.1:8000/public/editor.html

**Important:** Upload the assets (cloud-icon.jpg, dreambot.jpg, logo-text.jpg, intro.mp4) into `public/assets/` if they are missing.

## MCP Server

```bash
cd backend
python mcp_server.py
```

Add to your MCP config:

```json
{
  "mcpServers": {
    "dreambyte": {
      "command": "python",
      "args": ["/absolute/path/to/DreamByte-Studios/backend/mcp_server.py"],
      "env": { "DREAMBYTE_API": "http://127.0.0.1:8000" }
    }
  }
}
```

Tools: `list_models`, `get_animation_prompt`, `run_animation_script`, `animate_model`

## Structure

```
public/          # Landing + Editor + assets
backend/
  main.py        # FastAPI engine
  mcp_server.py  # MCP server
  requirements.txt
```

## Credits

Inspired by [Animato](https://github.com/otdnnc/Animato).

**DreamByte Studios** — Making animation accessible to every AI.

© 2026 DreamByte Studios
