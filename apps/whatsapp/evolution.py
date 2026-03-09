"""
Evolution API Client

Functions for sending messages and downloading media via Evolution API.
"""

import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


def get_evolution_config():
    """
    Get Evolution API configuration from environment variables.
    
    Returns:
        tuple: (api_url, instance_name, api_key)
        
    Raises:
        ValueError: If required environment variables are not set
    """
    api_url = os.environ.get("EVOLUTION_API_URL")
    instance_name = os.environ.get("EVOLUTION_INSTANCE_NAME")
    api_key = os.environ.get("EVOLUTION_API_KEY")
    
    if not api_url:
        raise ValueError("EVOLUTION_API_URL environment variable is required")
    if not instance_name:
        raise ValueError("EVOLUTION_INSTANCE_NAME environment variable is required")
    if not api_key:
        raise ValueError("EVOLUTION_API_KEY environment variable is required")
    
    # Remove trailing slash from URL if present
    api_url = api_url.rstrip("/")
    
    return api_url, instance_name, api_key


def get_headers() -> dict:
    """
    Get headers for Evolution API requests.
    
    Returns:
        dict: Headers with API key
    """
    _, _, api_key = get_evolution_config()
    return {"apikey": api_key}


def send_text_message(whatsapp_number: str, text: str) -> None:
    """
    Send a text message via Evolution API.
    
    Args:
        whatsapp_number: The recipient's WhatsApp number
        text: The message text to send
    """
    try:
        api_url, instance_name, _ = get_evolution_config()
        url = f"{api_url}/message/sendText/{instance_name}"
        
        payload = {
            "number": whatsapp_number,
            "text": text
        }
        
        response = requests.post(url, json=payload, headers=get_headers(), timeout=30)
        response.raise_for_status()
        logger.info(f"Sent text message to {whatsapp_number}")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send text message to {whatsapp_number}: {str(e)}")
        raise


def send_media_message(whatsapp_number: str, media_url: str, caption: str = "") -> None:
    """
    Send a media message (image) via Evolution API.
    
    Args:
        whatsapp_number: The recipient's WhatsApp number
        media_url: URL of the media to send
        caption: Optional caption for the media
    """
    try:
        api_url, instance_name, _ = get_evolution_config()
        url = f"{api_url}/message/sendMedia/{instance_name}"
        
        payload = {
            "number": whatsapp_number,
            "mediatype": "image",
            "media": media_url,
            "caption": caption
        }
        
        response = requests.post(url, json=payload, headers=get_headers(), timeout=30)
        response.raise_for_status()
        logger.info(f"Sent media message to {whatsapp_number}")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send media message to {whatsapp_number}: {str(e)}")
        raise


def download_image(url: str) -> Optional[bytes]:
    """
    Download an image from a URL.
    
    Args:
        url: The CDN URL to download from
        
    Returns:
        bytes or None: Raw image bytes or None on failure
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download image from {url}: {str(e)}")
        return None
