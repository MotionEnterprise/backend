"""
Centralized configuration for ComfyUI connection.

This follows the same pattern as core/database.py — one place to manage
the ComfyUI connection. Values come from Django settings (which read from .env).

To target a different ComfyUI pod, change settings.py (or .env) only.
This class is imported everywhere else — nothing else reads settings directly.
"""

import os
from django.conf import settings


class ComfyUIConfig:
    """
    Single source of truth for all ComfyUI connection settings.
    
    Properties:
        host: ComfyUI server hostname or IP
        port: ComfyUI server port
        protocol: HTTP or HTTPS
        ws_protocol: WebSocket protocol (ws or wss)
        base_url: Full HTTP base URL
        ws_url: Full WebSocket URL
        ws_timeout: WebSocket connection timeout in seconds
        request_timeout: HTTP request timeout in seconds
        api_key: Optional API key for ComfyUI authentication
    """

    @property
    def host(self) -> str:
        return getattr(settings, "COMFYUI_HOST", "127.0.0.1")

    @property
    def port(self) -> int:
        return int(getattr(settings, "COMFYUI_PORT", 8188))

    @property
    def protocol(self) -> str:
        return getattr(settings, "COMFYUI_PROTOCOL", "http")

    @property
    def ws_protocol(self) -> str:
        return getattr(settings, "COMFYUI_WS_PROTOCOL", "ws")

    @property
    def base_url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def ws_url(self) -> str:
        return f"{self.ws_protocol}://{self.host}:{self.port}"

    @property
    def ws_timeout(self) -> int:
        return int(getattr(settings, "COMFYUI_WS_TIMEOUT", 600))

    @property
    def request_timeout(self) -> int:
        return int(getattr(settings, "COMFYUI_REQUEST_TIMEOUT", 30))

    @property
    def api_key(self) -> str | None:
        """Optional API key for ComfyUI authentication."""
        return getattr(settings, "COMFYUI_API_KEY", None)


# Singleton — import this everywhere, never import settings directly
comfy_config = ComfyUIConfig()
