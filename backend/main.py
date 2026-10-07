"""
DreamByte Studios - Animation Engine Backend
Inspired by Animato (https://github.com/otdnnc/Animato)

Zero-cost local text-to-animation for rigged 3D models.
Supports OBJ / GLB / GLTF / FBX.
MCP-ready.
"""

from __future__ import annotations

import os
import uuid
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "public" / "upload"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="DreamByte Studios Animation Engine",
    description="Text-to-animation for rigged 3D models. Zero cost. MCP native.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/public", StaticFiles(directory=str(BASE_DIR / "public")), name="public")

class PromptRequest(BaseModel):
    filename: str
    message: str

class RunRequest(BaseModel):
    code: str
    filename: Optional[str] = None

class ChatRequest(BaseModel):
    filename: str
    message: str
    api_key: Optional[str] = None
    model: Optional[str] = "gemini-2.0-flash"

ALLOWED_EXTENSIONS = {".obj", ".fbx", ".glb", ".gltf"}

def safe_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in "._- ").strip()

def get_upload_path(filename: str) -> Path:
    return UPLOAD_DIR / safe_filename(filename)

@app.get("/")
async def root():
    return {"name": "DreamByte Studios Animation Engine", "version": "0.1.0", "mascot": "DreamBot", "docs": "/docs"}

@app.get("/api/health")
async def health():
    try:
        import bpy
        has_bpy = True
    except ImportError:
        has_bpy = False
    return {"status": "ok", "engine": "DreamByte", "bpy": has_bpy}

@app.post("/api/upload")
async def upload_model(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format. Allowed: {ALLOWED_EXTENSIONS}")
    filename = safe_filename(file.filename or f"model{ext}")
    target = get_upload_path(filename)
    if target.exists():
        stem = target.stem
        filename = f"{stem}_{uuid.uuid4().hex[:6]}{ext}"
        target = get_upload_path(filename)
    content = await file.read()
    target.write_bytes(content)
    return {"filename": filename, "size": len(content), "url": f"/public/upload/{filename}"}

@app.get("/api/files")
async def list_files():
    files = []
    for p in UPLOAD_DIR.iterdir():
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS:
            files.append({"filename": p.name, "size": p.stat().st_size, "url": f"/public/upload/{p.name}"})
    return files

@app.post("/api/prompt")
async def build_prompt(req: PromptRequest):
    path = get_upload_path(req.filename)
    if not path.exists():
        raise HTTPException(404, "Model not found")
    skeleton_info = _inspect_skeleton(path)
    prompt = f"""You are a Blender Python (bpy) expert. Write ONE self-contained Python script that:

1. Imports the model from this exact path: \"{path.as_posix()}\"
2. Animates the armature according to this request: \"{req.message}\"
3. Sets a reasonable frame range (e.g. 1-60 or 1-120) and fps 24 or 30
4. Bakes / exports the animation back into the SAME file, overwriting it.
   - For glTF/GLB: use export_animations=True
   - For FBX: use bake_anim=True

Skeleton / scene info:\n{skeleton_info}\n
Rules:
- Output ONLY valid Python code
- Use bpy 3.x / 4.x / 5.x compatible API
- Prefer pose.bones and keyframe_insert
"""
    return {"prompt": prompt, "filename": req.filename, "output_url": f"/public/upload/{req.filename}"}

def _inspect_skeleton(path: Path) -> str:
    try:
        import bpy
        bpy.ops.wm.read_factory_settings(use_empty=True)
        ext = path.suffix.lower()
        if ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=str(path))
        elif ext in (".glb", ".gltf"):
            bpy.ops.import_scene.gltf(filepath=str(path))
        elif ext == ".obj":
            bpy.ops.wm.obj_import(filepath=str(path))
        else:
            return f"Unsupported: {ext}"
        armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
        if not armatures:
            return "No armature found."
        lines = []
        for arm in armatures:
            lines.append(f"Armature: {arm.name}")
            for bone in arm.data.bones:
                parent = bone.parent.name if bone.parent else "None"
                lines.append(f"  - Bone: {bone.name} | parent: {parent}")
        return "\n".join(lines)
    except Exception as e:
        return f"(bpy not available: {e})\nAssume standard humanoid Mixamo-style skeleton (Hips, Spine, Chest, Neck, Head, arms, legs, etc.)."

@app.post("/api/run")
async def run_script(req: RunRequest):
    if not req.code.strip():
        raise HTTPException(400, "Empty code")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(req.code)
        script_path = f.name
    try:
        blender = shutil.which("blender")
        cmd = [blender, "--background", "--python", script_path] if blender else ["python3", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(BASE_DIR))
        return {"ok": result.returncode == 0, "returncode": result.returncode, "stdout": (result.stdout or "")[-4000:], "stderr": (result.stderr or "")[-4000:], "output_url": f"/public/upload/{req.filename}" if req.filename else None}
    except subprocess.TimeoutExpired:
        raise HTTPException(500, "Script timed out (300s)")
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass

@app.post("/api/chat")
async def chat_animate(req: ChatRequest):
    prompt_resp = await build_prompt(PromptRequest(filename=req.filename, message=req.message))
    return {"status": "prompt_ready", "prompt": prompt_resp["prompt"], "note": "Send this prompt to any LLM, then POST the returned code to /api/run", "filename": req.filename}

@app.get("/app")
async def serve_landing():
    index = BASE_DIR / "public" / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"error": "Landing not found"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
