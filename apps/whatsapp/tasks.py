"""
Celery tasks for WhatsApp ↔ ComfyUI integration.

This is the bridge: receives a WhatsApp session ID, fetches the user's image
from Supabase, uploads it to ComfyUI, runs the Flux2 workflow, downloads the
result, stores it back in Supabase, and delivers it to the user via WhatsApp.
"""

import asyncio
import logging
import tempfile
import os
from datetime import datetime

from celery import shared_task
from bson import ObjectId

logger = logging.getLogger(__name__)


def _get_image_from_supabase(file_path, bucket_name):
    """
    Retrieve image bytes from Supabase using the file path.

    Args:
        file_path: The file path in Supabase bucket
        bucket_name: The Supabase bucket name

    Returns:
        tuple: (bytes, content_type) or (None, None) on failure
    """
    from apps.media.supabase_storage import get_from_supabase, UPLOADED_MEDIA_BUCKET
    
    # Default to uploaded-media bucket if not specified
    bucket = bucket_name if bucket_name else UPLOADED_MEDIA_BUCKET
    
    image_bytes = get_from_supabase(bucket, file_path)
    
    if image_bytes is None:
        logger.error(f"Supabase file not found: {file_path} in {bucket}")
        return None, "image/jpeg"
    
    # Determine content type from file extension
    if file_path.endswith('.png'):
        content_type = "image/png"
    elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
        content_type = "image/jpeg"
    elif file_path.endswith('.webp'):
        content_type = "image/webp"
    else:
        content_type = "image/jpeg"
    
    return image_bytes, content_type


def _store_generated_image_in_supabase(image_bytes, sender, content_type="image/png"):
    """
    Store a generated image in Supabase (generated-media bucket).

    Args:
        image_bytes: Raw image bytes
        sender: WhatsApp number (for folder organization)
        content_type: MIME type

    Returns:
        str: The file path in Supabase
    """
    from apps.media.supabase_storage import save_generated_image, GENERATED_MEDIA_BUCKET
    
    file_path = save_generated_image(
        file_bytes=image_bytes,
        phone_number=sender,
        content_type=content_type,
    )

    logger.info(f"Stored generated image in Supabase: {file_path}")
    return file_path


@shared_task(bind=True, max_retries=1, default_retry_delay=10)
def run_whatsapp_generation(self, session_id: str):
    """
    Main Celery task: WhatsApp session → ComfyUI generation → deliver result.

    Args:
        session_id: The WhatsApp session's MongoDB ObjectId as a string.

    Flow:
        1. Load session from MongoDB
        2. Fetch input image from Supabase
        3. Upload input image to ComfyUI
        4. Build workflow with injected filename + prompt
        5. Submit workflow to ComfyUI
        6. Stream progress (wait for completion)
        7. Download generated output image from ComfyUI
        8. Store generated image in Supabase
        9. Send generated image to user via WhatsApp (Evolution API)
        10. Update session with generation metadata
        11. Send completion message
    """
    logger.info(f"[WhatsApp Gen] Starting generation for session {session_id}")

    # ── Step 1: Load session ──────────────────────────────────────────────
    from .models import WhatsAppSession, GenerationMeta, ImageMeta
    from .session import _get_dev_db, save_session

    _get_dev_db()

    try:
        session = WhatsAppSession.objects.get(id=ObjectId(session_id))
    except WhatsAppSession.DoesNotExist:
        logger.error(f"[WhatsApp Gen] Session {session_id} not found")
        return {"error": "Session not found"}

    sender = session.whatsapp_number
    logger.info(f"[WhatsApp Gen] Session loaded for {sender}, state={session.state}")

    try:
        # ── Step 2: Fetch input image from Supabase ──────────────────────────
        if not session.image or not session.image.file_path:
            raise ValueError("No input image in session")

        image_bytes, content_type = _get_image_from_supabase(
            session.image.file_path,
            session.image.bucket_name
        )
        if image_bytes is None:
            raise ValueError("Failed to fetch input image from Supabase")

        logger.info(
            f"[WhatsApp Gen] Fetched input image: "
            f"{len(image_bytes)} bytes, type={content_type}"
        )

        # ── Step 3: Upload input image to ComfyUI ────────────────────────
        from apps.comfyui.client import upload_file, make_client_id, submit_workflow, stream_progress, get_history, download_output_file

        # Determine file extension from content type
        ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
        ext = ext_map.get(content_type, "jpg")
        upload_filename = f"whatsapp_{sender}.{ext}"

        upload_result = asyncio.run(
            upload_file(
                file_bytes=image_bytes,
                filename=upload_filename,
                content_type=content_type,
            )
        )
        comfyui_filename = upload_result["name"]
        logger.info(f"[WhatsApp Gen] Uploaded to ComfyUI as: {comfyui_filename}")

        # ── Step 4: Build workflow ────────────────────────────────────────
        from .workflow_builder import build_workflow

        prompt_text = session.final_prompt or ""
        workflow = build_workflow(comfyui_filename, prompt_text)

        # ── Step 5: Submit workflow ───────────────────────────────────────
        client_id = make_client_id()
        prompt_id = asyncio.run(submit_workflow(workflow, client_id))

        logger.info(f"[WhatsApp Gen] Submitted workflow, prompt_id={prompt_id}")

        # Update session with ComfyUI tracking info
        session.generation = GenerationMeta(
            comfy_prompt_id=prompt_id,
            generation_status="running",
            started_at=datetime.utcnow(),
        )
        save_session(session)

        # ── Step 6: Stream progress (wait for completion) ─────────────────
        async def _wait_for_completion():
            async for event in stream_progress(client_id, prompt_id):
                event_type = event.get("type", "")
                if event_type == "progress":
                    pct = event.get("data", {}).get("percent", 0)
                    logger.debug(f"[WhatsApp Gen] Progress: {pct}%")
                if event.get("done"):
                    logger.info(f"[WhatsApp Gen] Workflow completed")
                    break

        asyncio.run(_wait_for_completion())

        # ── Step 7: Download output image ─────────────────────────────────
        history = asyncio.run(get_history(prompt_id))
        if not history:
            raise RuntimeError("Workflow completed but history not found")

        outputs = history.get("outputs", {})
        output_image_bytes = None
        output_filename = None

        for node_id, node_output in outputs.items():
            for img in node_output.get("images", []):
                if img.get("type") == "output":
                    output_filename = img["filename"]
                    subfolder = img.get("subfolder", "")
                    output_image_bytes = asyncio.run(
                        download_output_file(output_filename, subfolder, "output")
                    )
                    break
            if output_image_bytes:
                break

        if output_image_bytes is None or output_filename is None:
            raise RuntimeError("Failed to download output image from ComfyUI")

        logger.info(
            f"[WhatsApp Gen] Downloaded output: {output_filename} "
            f"({len(output_image_bytes)} bytes)"
        )

        # ── Step 8: Store generated image in Supabase ─────────────────────
        generated_file_path = _store_generated_image_in_supabase(
            output_image_bytes, sender
        )

        # ── Step 9: Send generated image to user via WhatsApp ─────────────
        from .evolution import send_media_message
        import base64

        try:
            # Convert binary image to base64 data URI for Evolution API
            b64_img = base64.b64encode(output_image_bytes).decode("utf-8")
            media_b64 = f"data:image/png;base64,{b64_img}"
            
            logger.info(f"[WhatsApp Gen] Sending image as base64 data URI to Evolution API")
            send_media_message(
                sender,
                b64_img,
                f"✨ Generated for {session.jewellery_type or 'jewellery'} — {session.image_type or 'custom'}"
            )
            logger.info(f"[WhatsApp Gen] Sent generated image to {sender}")
        except Exception as e:
            logger.error(f"[WhatsApp Gen] Failed to send media message: {e}")
            raise

        # ── Step 10: Update session ───────────────────────────────────────
        session.generation.generation_status = "completed"
        session.generation.completed_at = datetime.utcnow()
        session.generation.generated_image = ImageMeta(
            file_path=generated_file_path,
            bucket_name="generated-media",
            mimetype="image/png",
        )
        session.state = "completed"
        session.completed_at = datetime.utcnow()
        session.activeSession = False
        save_session(session)

        # ── Step 11: Send completion message ──────────────────────────────
        from .handlers.generating import send_generation_complete_message

        send_generation_complete_message(sender)

        logger.info(f"[WhatsApp Gen] ✅ Generation complete for {sender}")
        return {
            "session_id": session_id,
            "status": "completed",
            "generated_file_path": generated_file_path,
        }

    except Exception as exc:
        logger.error(f"[WhatsApp Gen] ❌ Failed for {sender}: {exc}", exc_info=True)

        # Update session with error
        try:
            from .evolution import send_text_message

            if session.generation:
                session.generation.generation_status = "failed"
                session.generation.error_message = str(exc)
            session.state = "completed"
            session.activeSession = False
            save_session(session)

            send_text_message(
                sender,
                "Sorry, image generation failed. Please try again.\n"
                "Send REDO to retry, or send a new image to start fresh."
            )
        except Exception as inner_exc:
            logger.error(f"[WhatsApp Gen] Failed to send error message: {inner_exc}")

        # Retry on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

        return {"session_id": session_id, "status": "failed", "error": str(exc)}
