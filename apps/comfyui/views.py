"""
DRF Views for ComfyUI integration.

Provides REST API endpoints for:
- Health checks
- File uploads
- Workflow submission
- Job status polling
- Output retrieval
- Queue management
"""

import asyncio
import logging

from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, parsers

from .models import ComfyJob
from .serializers import (
    ComfyJobSerializer,
    WorkflowSubmitSerializer,
    FileUploadSerializer,
)
from .tasks import run_comfyui_workflow
from .client import (
    upload_file,
    get_queue,
    interrupt_job,
    get_system_stats,
    download_output_file,
)
from .errors import ComfyConnectionError

logger = logging.getLogger(__name__)


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


class HealthView(APIView):
    """
    GET /comfyui/health/
    
    Health check endpoint that verifies:
    - API is running
    - ComfyUI is reachable
    - System stats are available
    """
    
    def get(self, request):
        try:
            stats = asyncio.run(get_system_stats())
            return Response({
                "api": "ok",
                "comfyui": "ok",
                "system": stats
            })
        except Exception as e:
            return Response(
                {"api": "ok", "comfyui": "unreachable", "error": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class UploadInputView(APIView):
    """
    POST /comfyui/upload/
    
    Upload an input image or video to ComfyUI before running a workflow.
    Returns the filename to inject into your workflow JSON.
    """
    
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    
    def post(self, request):
        ser = FileUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        uploaded = ser.validated_data["file"]
        file_bytes = uploaded.read()
        content_type = uploaded.content_type or "image/png"

        try:
            result = asyncio.run(
                upload_file(
                    file_bytes=file_bytes,
                    filename=uploaded.name,
                    content_type=content_type,
                    folder_type=ser.validated_data["folder_type"],
                    overwrite=ser.validated_data["overwrite"],
                )
            )
        except ComfyConnectionError as e:
            return Response(
                {"error": "Upload failed", "detail": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )

        return Response({
            "success": True,
            "filename": result["name"],    # ← inject this into workflow JSON
            "subfolder": result.get("subfolder", ""),
            "type": result.get("type"),
        })


class WorkflowSubmitView(APIView):
    """
    POST /comfyui/workflow/run/
    
    Submit a workflow. Returns job_id to track progress.
    Does NOT wait for the result — queues a Celery task.
    """
    
    def post(self, request):
        ser = WorkflowSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        # Create job record
        job = ComfyJob.objects.create(
            generation_id=ser.validated_data.get("generation_id"),
            status=ComfyJob.Status.PENDING,
        )

        logger.info(f"[ComfyUI] Created job {job.id} for generation {ser.validated_data.get('generation_id')}")

        # Queue the Celery task — returns immediately
        run_comfyui_workflow.delay(
            job_id=str(job.id),
            workflow=ser.validated_data["workflow"],
        )

        return Response(
            {"job_id": str(job.id), "status": "queued"},
            status=status.HTTP_202_ACCEPTED,
        )


class JobStatusView(APIView):
    """
    GET /comfyui/job/<uuid:job_id>/status/
    
    Poll job status (fallback if WebSocket isn't available to client).
    """
    
    def get(self, request, job_id):
        try:
            job = ComfyJob.objects.get(id=job_id)
        except ComfyJob.DoesNotExist:
            return Response(
                {"error": "Job not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(ComfyJobSerializer(job).data)


class JobOutputsView(APIView):
    """
    GET /comfyui/job/<uuid:job_id>/outputs/
    
    Returns list of output files with download URLs.
    """
    
    def get(self, request, job_id):
        try:
            job = ComfyJob.objects.get(id=job_id)
        except ComfyJob.DoesNotExist:
            return Response(
                {"error": "Job not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if job.status != ComfyJob.Status.COMPLETE:
            return Response(
                {"error": "Job not complete yet", "status": job.status},
                status=status.HTTP_202_ACCEPTED,
            )

        # Enrich each file with a download URL
        files = []
        for f in job.output_files:
            files.append({
                **f,
                "download_url": f"/comfyui/download/?filename={f['filename']}&subfolder={f.get('subfolder','')}&type=output",
            })

        return Response({"job_id": str(job_id), "files": files})


class FileDownloadView(APIView):
    """
    GET /comfyui/download/?filename=&subfolder=&type=output
    
    Proxy-download a file directly from ComfyUI (useful before Supabase save completes).
    For final access, prefer the Media App Supabase URL.
    """
    
    def get(self, request):
        filename = request.query_params.get("filename")
        subfolder = request.query_params.get("subfolder", "")
        file_type = request.query_params.get("type", "output")

        if not filename:
            return Response(
                {"error": "filename required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            file_bytes = asyncio.run(
                download_output_file(filename, subfolder, file_type)
            )
        except ComfyConnectionError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )

        content_type = _mime(filename)
        response = HttpResponse(file_bytes, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class QueueView(APIView):
    """
    GET /comfyui/queue/
    
    View ComfyUI's internal queue.
    """
    
    def get(self, request):
        try:
            data = asyncio.run(get_queue())
            return Response(data)
        except ComfyConnectionError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )


class InterruptView(APIView):
    """
    POST /comfyui/queue/interrupt/
    
    Stop current job running on ComfyUI.
    """
    
    def post(self, request):
        try:
            asyncio.run(interrupt_job())
            return Response({"status": "interrupted"})
        except ComfyConnectionError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )
