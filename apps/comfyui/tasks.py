"""
Celery tasks for ComfyUI integration.

This is the engine room. DRF views don't call ComfyUI directly —
they queue these tasks and return immediately.
"""

import asyncio
import logging

from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .client import (
    make_client_id,
    submit_workflow,
    stream_progress,
    get_history,
    download_output_file,
)
from .models import ComfyJob
from .errors import ComfyAPIError, ComfyExecutionError, ComfyTimeoutError

logger = logging.getLogger(__name__)


def _push_ws_event(job_id: str, event: dict):
    """Push a progress event to the Channels WebSocket group for this job."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"comfy_job_{job_id}",
        {"type": "job.progress", "event": event},
    )


def _mime(filename: str) -> str:
    """Get MIME type from filename extension."""
    ext = filename.lower().rsplit(".", 1)[-1]
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "gif": "image/gif",
        "mp4": "video/mp4",
        "webm": "video/webm",
    }.get(ext, "application/octet-stream")


def _extract_output_files(outputs: dict) -> list[dict]:
    """Parse ComfyUI history outputs into a flat list."""
    files = []
    for node_id, node_output in outputs.items():
        for img in node_output.get("images", []):
            if img.get("type") == "output":
                files.append({
                    "filename": img["filename"],
                    "subfolder": img.get("subfolder", ""),
                    "file_type": "image",
                    "content_type": _mime(img["filename"]),
                    "node_id": node_id,
                })
        for vid in node_output.get("videos", []):
            files.append({
                "filename": vid["filename"],
                "subfolder": vid.get("subfolder", ""),
                "file_type": "video",
                "content_type": _mime(vid["filename"]),
                "node_id": node_id,
            })
    return files


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def run_comfyui_workflow(self, job_id: str, workflow: dict, input_files: list = None):
    """
    Main Celery task for running a ComfyUI generation.
    
    Args:
        job_id:      The ComfyJob.id (UUID string) — used to push WS events
        workflow:    The full workflow_api.json dict (possibly with injected filenames)
        input_files: Optional list of already-uploaded ComfyUI filenames
    
    Flow:
        1. Mark job as RUNNING
        2. Submit workflow to ComfyUI
        3. Stream WebSocket progress → push to Channels group → client sees it
        4. On complete → fetch history → download files → save to Media App (GridFS)
        5. Mark job as COMPLETE (or FAILED)
    """
    logger.info(f"[ComfyJob {job_id}] Starting workflow execution")
    
    try:
        job = ComfyJob.objects.get(id=job_id)
    except ComfyJob.DoesNotExist:
        logger.error(f"[ComfyJob {job_id}] Job not found")
        return

    try:
        # Step 1: Mark running
        job.status = ComfyJob.Status.RUNNING
        job.save(update_fields=["status"])

        # Step 2: Submit
        client_id = make_client_id()
        job.client_id = client_id
        job.save(update_fields=["client_id"])

        prompt_id = asyncio.run(submit_workflow(workflow, client_id))
        job.prompt_id = prompt_id
        job.save(update_fields=["prompt_id"])

        logger.info(f"[ComfyJob {job_id}] Submitted → prompt_id={prompt_id}")

        # Step 3: Stream progress via WebSocket
        async def _stream():
            async for event in stream_progress(client_id, prompt_id):
                # Push to Channels group (client's WebSocket consumer listens here)
                _push_ws_event(job_id, event)
                if event.get("done"):
                    break

        asyncio.run(_stream())

        # Step 4: Fetch outputs
        history = asyncio.run(get_history(prompt_id))
        if not history:
            raise ComfyAPIError("Job completed but history not found")

        output_files = _extract_output_files(history.get("outputs", {}))
        saved_files = []

        for file_info in output_files:
            # Download raw bytes from ComfyUI
            file_bytes = asyncio.run(
                download_output_file(
                    file_info["filename"],
                    file_info["subfolder"],
                    "output",
                )
            )
            
            # Save to Media App (Supabase)
            try:
                from apps.media.supabase_storage import save_generated_image, GENERATED_MEDIA_BUCKET
                
                # For ComfyUI jobs, we need a phone number for organization
                # Use job_id as a fallback identifier
                phone_number = f"job_{job_id[:8]}" if job_id else "unknown"
                
                file_path = save_generated_image(
                    file_bytes=file_bytes,
                    phone_number=phone_number,
                    content_type=file_info["content_type"],
                )
                saved_files.append({
                    **file_info, 
                    "file_path": file_path,
                    "bucket_name": GENERATED_MEDIA_BUCKET
                })
            except ImportError:
                # Media app storage not available yet - store raw file info
                logger.warning(f"[ComfyJob {job_id}] Media app not available, storing file info without Supabase")
                saved_files.append({**file_info, "file_path": None, "bucket_name": None})

        # Step 5: Mark complete
        job.status = ComfyJob.Status.COMPLETE
        job.output_files = saved_files
        job.save(update_fields=["status", "output_files"])

        _push_ws_event(job_id, {
            "type": "job_complete",
            "data": {"files": saved_files},
            "done": True,
        })

        logger.info(f"[ComfyJob {job_id}] Complete — {len(saved_files)} file(s) saved")
        return {"job_id": job_id, "files": saved_files}

    except (ComfyExecutionError, ComfyTimeoutError) as exc:
        logger.error(f"[ComfyJob {job_id}] Failed: {exc}")
        job.status = ComfyJob.Status.FAILED
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message"])
        _push_ws_event(job_id, {"type": "error", "data": {"message": str(exc)}, "done": True})
        raise  # Celery will mark the task as FAILURE

    except ComfyAPIError as exc:
        logger.error(f"[ComfyJob {job_id}] Retrying: {exc}")
        job.status = ComfyJob.Status.PENDING
        job.save(update_fields=["status"])
        raise self.retry(exc=exc)
