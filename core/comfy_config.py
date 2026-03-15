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
        api_path: API path prefix (e.g., "/api" for cloud.comfy.org)
        port: ComfyUI server port
        protocol: HTTP or HTTPS
        ws_protocol: WebSocket protocol (ws or wss)
        base_url: Full HTTP base URL (includes api_path)
        ws_url: Full WebSocket URL
        ws_timeout: WebSocket connection timeout in seconds
        request_timeout: HTTP request timeout in seconds
        api_key: Optional API key for ComfyUI Cloud authentication
        headers: Dict of headers including X-API-Key if configured
    """

    @property
    def host(self) -> str:
        return getattr(settings, "COMFYUI_HOST", "127.0.0.1")

    @property
    def api_path(self) -> str:
        """API path prefix (e.g., "/api" for cloud.comfy.org, "" for local)."""
        return getattr(settings, "COMFYUI_API_PATH", "")

    @property
    def port(self) -> int:
        return int(getattr(settings, "COMFYUI_PORT", 8188))

    @property
    def protocol(self) -> str:
        return getattr(settings, "COMFYUI_PROTOCOL", "http")

    @property
    def ws_protocol(self) -> str:
        # If explicitly set in settings, use that
        if hasattr(settings, "COMFYUI_WS_PROTOCOL"):
            val = getattr(settings, "COMFYUI_WS_PROTOCOL")
            if val in ["ws", "wss"]:
                return val
        # Otherwise infer from the HTTP protocol
        return "wss" if self.protocol == "https" else "ws"

    @property
    def base_url(self) -> str:
        """Full HTTP base URL including API path."""
        path = self.api_path.rstrip('/')
        return f"{self.protocol}://{self.host}{path}"

    @property
    def ws_url(self) -> str:
        """Full WebSocket URL (without API path, just host)."""
        return f"{self.ws_protocol}://{self.host}"

    @property
    def ws_timeout(self) -> int:
        return int(getattr(settings, "COMFYUI_WS_TIMEOUT", 600))

    @property
    def request_timeout(self) -> int:
        return int(getattr(settings, "COMFYUI_REQUEST_TIMEOUT", 30))

    @property
    def api_key(self) -> str | None:
        """Optional API key for ComfyUI Cloud authentication."""
        return getattr(settings, "COMFYUI_API_KEY", None)

    @property
    def headers(self) -> dict:
        """HTTP headers including API key if configured."""
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers


# Singleton — import this everywhere, never import settings directly
comfy_config = ComfyUIConfig()
