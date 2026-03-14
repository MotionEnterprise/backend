"""
ComfyUI Django App Configuration

Defines the ComfyUI application for Django.
"""

from django.apps import AppConfig


class ComfyUIConfig(AppConfig):
    """
    Configuration for the ComfyUI integration app.
    
    This app provides:
    - REST API endpoints for submitting workflows and tracking jobs
    - WebSocket consumer for real-time progress updates
    - Celery tasks for async communication with ComfyUI
    - Models for tracking generation jobs
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.comfyui'
    verbose_name = 'ComfyUI Integration'
    
    def ready(self):
        """
        Initialize app when Django starts.
        
        Import signals or perform initialization here if needed.
        """
        pass
