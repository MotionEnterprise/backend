"""
Evolution API Client

Functions for sending messages and downloading media via Evolution API.
"""

import os
import logging
import requests
import base64
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
        # 1️⃣ download image from supabase
        # img_data = requests.get(media_url).content

        # 2️⃣ convert to base64
        # media_base64 = base64.b64encode(img_data).decode()
        payload = {
            "number": whatsapp_number,
            "mediatype": "image",
            "mimetype": "image/jpeg",
            "media": media_url,
            "caption": caption
        }
        print(payload)
        
        
        response = requests.post(url, json=payload, headers=get_headers(), timeout=30)
        response.raise_for_status()
        logger.info(f"Sent media message to {whatsapp_number}")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send media message to {whatsapp_number}: {str(e)}")
        raise


def get_image_from_evolution_api(message_key_id: str) -> Optional[bytes]:
    """
    Get image in base64 format from Evolution API using message key ID,
    then decode to binary.
    
    Endpoint: POST /chat/getBase64FromMediaMessage/{instance_name}
    Body: {"messageKey": {"id": "message_key_id"}}
    
    Args:
        message_key_id: The message key ID from data.key.id
        
    Returns:
        bytes or None: Raw image bytes or None on failure
    """
    import base64
    
    try:
        api_url, instance_name, _ = get_evolution_config()
        url = f"{api_url}/chat/getBase64FromMediaMessage/{instance_name}"
        
        payload = {
            "message": {
                "key": {
                    "id": message_key_id
                }
            }
        }
        
        response = requests.post(url, json=payload, headers=get_headers(), timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Get base64 string from response
        base64_string = data.get("base64") or data.get("media")
        
        if base64_string:
            # Decode base64 to binary
            image_bytes = base64.b64decode(base64_string)
            logger.info(f"Successfully fetched and decoded image for message {message_key_id}")
            return image_bytes
        
        logger.warning(f"No base64 in response for message {message_key_id}: {data}")
        return None
        
    except Exception as e:
        logger.error(f"Failed to get image from Evolution API for {message_key_id}: {str(e)}")
        return None


def download_image(url: str, message_key_id: Optional[str] = None) -> Optional[bytes]:
    """
    Download an image. If message_key_id is provided, fetch base64 from 
    Evolution API and decode to binary.
    
    Args:
        url: The CDN URL to download from (can be empty if using message_key_id)
        message_key_id: Optional message key ID to fetch base64 from Evolution API
        
    Returns:
        bytes or None: Raw image bytes or None on failure
    """
    # If we have a message_key_id, use Evolution API to get base64
    if message_key_id:
        image_bytes = get_image_from_evolution_api(message_key_id)
        if image_bytes:
            return image_bytes
        # Fallback: try URL anyway if Evolution API fails
    
    # Fallback to URL download
    if url:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download image from {url}: {str(e)}")
            return None
    
    return None
