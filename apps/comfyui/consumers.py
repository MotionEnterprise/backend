"""
Django Channels WebSocket Consumer for real-time ComfyUI progress.

Provides WebSocket endpoint for clients to receive real-time
updates about ComfyUI job progress.
"""

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class ComfyProgressConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer: ws://your-api/ws/comfyui/job/<job_id>/progress/
    
    How it works:
    1. Client connects with job_id in URL
    2. Consumer joins the Channels group: "comfy_job_{job_id}"
    3. Celery task pushes events to that group as it processes
    4. Consumer forwards those events to the connected client
    
    The Celery task and this consumer are DECOUPLED — the task
    doesn't know about WebSocket clients; it just broadcasts to the group.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.job_id = self.scope["url_route"]["kwargs"]["job_id"]
        self.group_name = f"comfy_job_{self.job_id}"

        # Join the job's channel group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        
        await self.accept()

        logger.info(f"[WebSocket] Client connected to job {self.job_id}")

        # Send initial status from DB
        try:
            job = await sync_to_async(
                lambda: __import__('apps.comfyui.models', fromlist=['ComfyJob']).ComfyJob.objects.get(id=self.job_id)
            )()
            await self.send(text_data=json.dumps({
                "type": "initial_status",
                "data": {
                    "status": job.status,
                    "job_id": str(job.id)
                },
                "done": job.status in ["complete", "failed"],
            }))
        except Exception as e:
            logger.warning(f"[WebSocket] Could not fetch job {self.job_id}: {e}")
            await self.send(text_data=json.dumps({
                "type": "error",
                "data": {"message": "Job not found"},
                "done": True
            }))
            await self.close()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"[WebSocket] Client disconnected from job {self.job_id}")

    async def job_progress(self, event):
        """
        Forward Celery task events to the WebSocket client.
        
        This handler is called when Celery task does group_send
        with type "job.progress".
        """
        await self.send(text_data=json.dumps(event["event"]))
