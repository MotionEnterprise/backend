"""
Evolution API Payload Parser

Parses incoming webhook payloads from Evolution API.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class IncomingMessage:
    """
    Data class for parsed incoming messages.
    """
    sender: str  # Clean number, no @s.whatsapp.net
    type: str  # "text" | "image" | "unknown"
    text: Optional[str] = None
    image_url: Optional[str] = None
    mimetype: Optional[str] = None


def parse_evolution_payload(data: dict) -> Optional[IncomingMessage]:
    """
    Parse Evolution API webhook payload.
    
    Handles both "messages.upsert" (lowercase) and "MESSAGES_UPSERT" (uppercase)
    event types.
    
    Args:
        data: The webhook payload dictionary
        
    Returns:
        IncomingMessage or None: Parsed message or None if invalid
    """
    # Get event type (handle both formats)
    event = data.get("event", "")
    if event not in ("messages.upsert", "MESSAGES_UPSERT"):
        return None
    
    # Get data payload
    data_payload = data.get("data", {})
    if not data_payload:
        return None
    
    # Check if from me (ignore bot's own messages)
    key = data_payload.get("key", {})
    from_me = key.get("fromMe", False)
    if from_me:
        return None
    
    # Get sender number - use remoteJid from the message key (the person who sent the message)
    remote_jid = key.get("remoteJid", "")
    if not remote_jid:
        return None
    
    # Use remoteJid as sender, strip @s.whatsapp.net suffix
    sender = remote_jid
    if "@s.whatsapp.net" in sender:
        sender = sender.split("@s.whatsapp.net")[0]
    
    # Get message content
    message = data_payload.get("message", {})
    
    # Check for image message
    if "imageMessage" in message:
        image_msg = message["imageMessage"]
        image_url = image_msg.get("url")
        mimetype = image_msg.get("mimetype", "image/jpeg")
        
        if image_url:
            return IncomingMessage(
                sender=sender,
                type="image",
                image_url=image_url,
                mimetype=mimetype
            )
    
    # Check for text message (conversation)
    if "conversation" in message:
        text = message.get("conversation", "").strip()
        if text:
            return IncomingMessage(
                sender=sender,
                type="text",
                text=text
            )
    
    # Check for extended text message
    if "extendedTextMessage" in message:
        text = message.get("extendedTextMessage", {}).get("text", "").strip()
        if text:
            return IncomingMessage(
                sender=sender,
                type="text",
                text=text
            )
    
    # Unknown message type
    return IncomingMessage(
        sender=sender,
        type="unknown"
    )
