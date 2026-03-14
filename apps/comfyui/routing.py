"""
WebSocket routing for ComfyUI Django app.

Provides WebSocket endpoints for real-time job progress streaming.
"""

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/comfyui/job/(?P<job_id>[^/]+)/progress/$',
        consumers.ComfyProgressConsumer.as_asgi()
    ),
]
