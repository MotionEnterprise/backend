"""
ComfyUI Django Application

Integration module for connecting GrafX Backend to ComfyUI
for AI-powered image generation workflows.

This app provides:
- REST API endpoints for workflow submission and job tracking
- WebSocket consumer for real-time progress streaming
- Celery tasks for async ComfyUI communication
- Django models for job tracking
"""

default_app_config = 'apps.comfyui.apps.ComfyUIConfig'
