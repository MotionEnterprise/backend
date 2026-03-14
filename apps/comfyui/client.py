"""
ComfyUI Client - Async HTTP and WebSocket communication with ComfyUI.

Pure async functions for communicating with ComfyUI API.
No Django ORM, no Celery - just raw ComfyUI calls.
"""

import uuid
import json
import asyncio
from typing import AsyncGenerator

import aiohttp
import websockets

from core.comfy_config import comfy_config
from .errors import (
    ComfyConnectionError,
    ComfyValidationError,
    ComfyTimeoutError,
    ComfyExecutionError,
)


def make_client_id() -> str:
    """Generate a unique client ID for WebSocket connections."""
    return str(uuid.uuid4())


async def submit_workflow(workflow: dict, client_id: str) -> str:
    """
    POST /prompt — queue a workflow.
    Returns prompt_id string.
    
    Raises:
        ComfyValidationError: If workflow has node errors.
        ComfyConnectionError: If ComfyUI is unreachable.
    """
    url = f"{comfy_config.base_url}/prompt"
    payload = {"prompt": workflow, "client_id": client_id}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=comfy_config.request_timeout),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise ComfyConnectionError(
                        f"ComfyUI returned HTTP {resp.status}: {body}"
                    )
                data = await resp.json()

    except aiohttp.ClientConnectorError as e:
        raise ComfyConnectionError(
            f"Cannot reach ComfyUI at {comfy_config.base_url}: {e}"
        )

    if data.get("node_errors"):
        raise ComfyValidationError(
            "Workflow has node errors", node_errors=data["node_errors"]
        )

    return data["prompt_id"]


async def upload_file(
    file_bytes: bytes,
    filename: str,
    content_type: str = "image/png",
    folder_type: str = "input",
    overwrite: bool = True,
) -> dict:
    """
    POST /upload/image — upload an input file to ComfyUI.
    Returns {"name": str, "subfolder": str, "type": str}.
    """
    url = f"{comfy_config.base_url}/upload/image"
    form = aiohttp.FormData()
    form.add_field("image", file_bytes, filename=filename, content_type=content_type)
    form.add_field("type", folder_type)
    form.add_field("overwrite", "true" if overwrite else "false")

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=form) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise ComfyConnectionError(
                    f"Upload failed ({filename}): HTTP {resp.status} — {body}"
                )
            return await resp.json()


async def get_history(prompt_id: str) -> dict:
    """
    GET /history/{prompt_id}
    Returns the job's output dict, or {} if not found yet.
    """
    url = f"{comfy_config.base_url}/history/{prompt_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 404:
                return {}
            data = await resp.json()
            return data.get(prompt_id, {})


async def download_output_file(
    filename: str, subfolder: str = "", file_type: str = "output"
) -> bytes:
    """
    GET /view — fetch raw bytes of a generated file (image or video).
    """
    url = f"{comfy_config.base_url}/view"
    params = {"filename": filename, "subfolder": subfolder, "type": file_type}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                raise ComfyConnectionError(
                    f"Download failed ({filename}): HTTP {resp.status}"
                )
            return await resp.read()


async def get_queue() -> dict:
    """GET /queue"""
    url = f"{comfy_config.base_url}/queue"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()


async def interrupt_job() -> None:
    """POST /interrupt — stop the current job."""
    url = f"{comfy_config.base_url}/interrupt"
    async with aiohttp.ClientSession() as session:
        await session.post(url)


async def get_system_stats() -> dict:
    """GET /system_stats — for health checks."""
    url = f"{comfy_config.base_url}/system_stats"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()


async def stream_progress(
    client_id: str, prompt_id: str
) -> AsyncGenerator[dict, None]:
    """
    Connect to ComfyUI WebSocket and yield progress events.
    
    Yields dicts:
      {"type": "progress",  "data": {"step": 5, "total": 20, "percent": 25}, "done": False}
      {"type": "executing", "data": {"node_id": "3"},                         "done": False}
      {"type": "executed",  "data": {"images": [...]},                        "done": False}
      {"type": "complete", "data": {},                                        "done": True}
    
    Raises:
        ComfyExecutionError: On ComfyUI-side error.
        ComfyTimeoutError: On timeout.
    """
    ws_url = f"{comfy_config.ws_url}/ws?clientId={client_id}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                ws_url,
                timeout=10.0,
                receive_timeout=30.0,
                autoping=True,
                heartbeat=20.0
            ) as ws:
                async for raw_msg in ws:
                    if raw_msg.type == aiohttp.WSMsgType.BINARY:
                        # Binary = preview frame, skip JSON parsing
                        yield {"type": "preview", "data": {"size": len(raw_msg.data)}, "done": False}
                        continue
                    elif raw_msg.type == aiohttp.WSMsgType.TEXT:
                        msg = json.loads(raw_msg.data)
                        msg_type = msg.get("type")
                        msg_data = msg.get("data", {})
                        msg_prompt_id = msg_data.get("prompt_id")

                        if msg_type == "progress":
                            step = msg_data.get("value", 0)
                            total = max(msg_data.get("max", 1), 1)
                            yield {
                                "type": "progress",
                                "data": {"step": step, "total": total, "percent": round(step / total * 100)},
                                "prompt_id": prompt_id,
                                "done": False,
                            }

                        elif msg_type == "executing":
                            node_id = msg_data.get("node")
                            if node_id is None and msg_prompt_id == prompt_id:
                                yield {"type": "complete", "data": {}, "prompt_id": prompt_id, "done": True}
                                return
                            yield {
                                "type": "executing",
                                "data": {"node_id": node_id},
                                "prompt_id": prompt_id,
                                "done": False,
                            }

                        elif msg_type == "executed":
                            yield {
                                "type": "executed",
                                "data": msg_data.get("output", {}),
                                "prompt_id": prompt_id,
                                "done": False,
                            }

                        elif msg_type == "execution_error":
                            raise ComfyExecutionError(
                                msg_data.get("exception_message", "Unknown execution error"),
                                node_id=msg_data.get("node_id"),
                                node_type=msg_data.get("node_type"),
                            )

                        elif msg_type == "status":
                            yield {"type": "status", "data": msg_data, "prompt_id": prompt_id, "done": False}
                    
                    elif raw_msg.type == aiohttp.WSMsgType.ERROR:
                        raise ComfyConnectionError(f"WebSocket error: {ws.exception()}")
                    
                    elif raw_msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING):
                        break

    except aiohttp.ClientError as e:
        raise ComfyConnectionError(f"WebSocket connection error: {e}")
    except asyncio.TimeoutError:
        raise ComfyTimeoutError(f"Timed out waiting for workflow {prompt_id}")
