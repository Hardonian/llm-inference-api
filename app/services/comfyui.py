"""ComfyUI integration service."""
import os
import json
import time
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger("comfyui_svc")

COMFYUI_BASE = "http://localhost:8188"
COMFYUI_ROOT = Path(os.environ.get("COMFYUI_ROOT", "/opt/ai/comfyui/ComfyUI"))
COMFYUI_MODELS_DIR = str(COMFYUI_ROOT / "models")
COMFYUI_INPUT_DIR = str(COMFYUI_ROOT / "input")
WORKFLOWS_DIR = "/home/scott/ai-lab/image/workflows"


class ComfyUIService:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=COMFYUI_BASE, timeout=30.0)
        self._models_cache: List[Dict] = []
        self._nodes_cache: List[Dict] = []
        self._workflows_cache: List[Dict] = []
        self._cache_time = 0
        self._cache_ttl = 30

    async def close(self):
        await self.client.aclose()

    # ========================================
    # System Stats & Health
    # ========================================
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get ComfyUI system statistics."""
        try:
            resp = await self.client.get("/system_stats")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return {}

    async def health_check(self) -> bool:
        """Check if ComfyUI is responsive."""
        try:
            resp = await self.client.get("/system_stats", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    # ========================================
    # Models Management
    # ========================================
    async def list_models(self) -> List[Dict[str, Any]]:
        """List all available models from ComfyUI."""
        try:
            resp = await self.client.get("/object_info")
            resp.raise_for_status()
            data = resp.json()

            models = []
            # Check various model directories
            for node_id, node_info in data.items():
                class_type = node_info.get("class_type")
                if class_type in ["CheckpointLoaderSimple", "LoadLoRA", "VAELoader", "CLIPLoader"]:
                    input_def = node_info.get("input", {}).get("required", {})
                    for input_name, spec in input_def.items():
                        if isinstance(spec, list) and spec and spec[0] in ["STRING", "COMBO"]:
                            if "ckpt_name" in input_name or "model_name" in input_name or "lora_name" in input_name:
                                options = spec[1] if len(spec) > 1 else []
                                for opt in options:
                                    if isinstance(opt, str):
                                        models.append({
                                            "name": opt,
                                            "type": class_type,
                                            "source": "comfyui"
                                        })
            return models
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def scan_model_directories(self) -> List[Dict[str, Any]]:
        """Scan ComfyUI model directories for files."""
        models = []
        model_types = {
            "checkpoints": "checkpoint",
            "loras": "lora",
            "vae": "vae",
            "embeddings": "embedding",
            "controlnet": "controlnet",
            "upscale_models": "upscaler",
            "diffusion_models": "diffusion",
            "text_encoders": "text_encoder",
            "clip": "clip",
            "clip_vision": "clip_vision",
            "unet": "unet",
        }

        for folder, mtype in model_types.items():
            path = Path(COMFYUI_MODELS_DIR) / folder
            if path.exists():
                for file_path in path.rglob("*"):
                    if file_path.is_file() and not file_path.name.startswith("."):
                        stat = file_path.stat()
                        models.append({
                            "name": file_path.name,
                            "type": mtype,
                            "size": self._format_size(stat.st_size),
                            "size_bytes": stat.st_size,
                            "path": str(file_path.relative_to(COMFYUI_MODELS_DIR)),
                            "downloaded_at": int(stat.st_mtime),
                        })
        return models

    async def download_model(self, url: str, model_type: str, target_folder: Optional[str] = None) -> Dict[str, Any]:
        """Download a model from URL to the active ComfyUI models directory."""
        folder_by_type = {
            "checkpoint": "checkpoints",
            "lora": "loras",
            "vae": "vae",
            "embedding": "embeddings",
            "controlnet": "controlnet",
            "upscaler": "upscale_models",
            "diffusion": "diffusion_models",
            "text_encoder": "text_encoders",
            "clip": "clip",
            "clip_vision": "clip_vision",
        }
        allowed_folders = set(folder_by_type.values()) | {"diffusion_models", "text_encoders", "clip", "clip_vision", "unet"}
        target_folder = target_folder or folder_by_type.get(model_type, "checkpoints")
        if target_folder not in allowed_folders:
            raise ValueError(f"Invalid target folder: {target_folder}")

        target_dir = Path(COMFYUI_MODELS_DIR) / target_folder
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = url.split("/")[-1].split("?")[0]
        if not filename:
            filename = f"model_{int(time.time())}"

        target_path = target_dir / filename
        if target_path.exists():
            return {
                "name": filename,
                "type": model_type,
                "size": self._format_size(target_path.stat().st_size),
                "path": str(target_path.relative_to(COMFYUI_MODELS_DIR)),
                "already_exists": True,
            }

        async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(target_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)

        return {
            "name": filename,
            "type": model_type,
            "size": self._format_size(target_path.stat().st_size),
            "path": str(target_path.relative_to(COMFYUI_MODELS_DIR)),
        }

    def _format_size(self, bytes_val: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024:
                return f"{bytes_val:.1f}{unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f}TB"

    # ========================================
    # Nodes Management
    # ========================================
    async def list_custom_nodes(self) -> List[Dict[str, Any]]:
        """List installed custom nodes."""
        try:
            resp = await self.client.get("/extensions")
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return [
                    {
                        "name": Path(str(item)).stem or str(item),
                        "version": "installed",
                        "author": "local",
                        "path": str(item),
                    }
                    for item in data
                ]
            return data
        except Exception as e:
            logger.error(f"Failed to list extensions: {e}")
            return []

    async def install_custom_node(self, repo_url: str) -> Dict[str, Any]:
        """Install a custom node from GitHub repo."""
        # This would typically use comfy-cli or git
        # For now, return instructions
        return {
            "instruction": f"Run: cd /home/scott/ai-lab/image/comfyui/custom_nodes && git clone {repo_url}",
            "note": "Restart ComfyUI after installing nodes",
        }

    # ========================================
    # Workflows Management
    # ========================================
    async def list_workflows(self) -> List[Dict[str, Any]]:
        """List saved workflows."""
        workflows = []
        if Path(WORKFLOWS_DIR).exists():
            for file_path in Path(WORKFLOWS_DIR).glob("*.json"):
                try:
                    with open(file_path) as f:
                        wf = json.load(f)
                    stat = file_path.stat()
                    api_graph = wf.get("api_workflow") if isinstance(wf.get("api_workflow"), dict) else wf
                    node_count = len(api_graph) if isinstance(api_graph, dict) else len(wf.get("nodes", []))
                    workflows.append({
                        "id": file_path.stem,
                        "name": wf.get("name", file_path.stem),
                        "nodes": node_count,
                        "node_count": node_count,
                        "updated": int(stat.st_mtime),
                        "description": wf.get("description", ""),
                        "tags": wf.get("tags", []),
                        "is_mature": wf.get("is_mature", False),
                    })
                except Exception:
                    pass
        return workflows

    async def get_workflow(self, workflow_id: str) -> Optional[Dict]:
        """Get a specific workflow by ID."""
        path = Path(WORKFLOWS_DIR) / f"{workflow_id}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None

    async def save_workflow(self, workflow: Dict[str, Any]) -> str:
        """Save a workflow."""
        Path(WORKFLOWS_DIR).mkdir(parents=True, exist_ok=True)
        workflow_id = workflow.get("id") or f"wf_{int(time.time())}"
        workflow["id"] = workflow_id
        workflow["updated"] = int(time.time())
        if "created_at" not in workflow:
            workflow["created_at"] = int(time.time())

        path = Path(WORKFLOWS_DIR) / f"{workflow_id}.json"
        with open(path, "w") as f:
            json.dump(workflow, f, indent=2)
        return workflow_id

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        path = Path(WORKFLOWS_DIR) / f"{workflow_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    async def queue_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Queue a workflow to ComfyUI."""
        try:
            prompt = workflow.get("api_workflow") if isinstance(workflow.get("api_workflow"), dict) else workflow
            resp = await self.client.post("/prompt", json={"prompt": prompt})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to queue workflow: {e}")
            raise

    # ========================================
    # Queue & History
    # ========================================
    async def get_queue(self) -> Dict[str, Any]:
        """Get current queue status."""
        try:
            resp = await self.client.get("/queue")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to get queue: {e}")
            return {"running": [], "pending": []}

    async def get_history(self, prompt_id: str) -> Optional[Dict]:
        """Get generation history for a prompt."""
        try:
            resp = await self.client.get(f"/history/{prompt_id}")
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
        return None


comfyui_service = ComfyUIService()