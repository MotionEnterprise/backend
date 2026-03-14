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
    message_key_id: Optional[str] = None  # The key.id from message for fetching base64 from Evolution API


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
    
    # print(f'data - \n{data}')

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
        
        # Get message key ID - needed to fetch base64 from Evolution API
        # This is from data.key.id, not from imageMessage
        message_key_id = key.get("id")
        
        # Get mimetype
        mimetype = image_msg.get("mimetype", "image/jpeg")
        
        print(f'message_key_id - {message_key_id}')
        
        if message_key_id:
            return IncomingMessage(
                sender=sender,
                type="image",
                image_url="",  # Will be fetched via Evolution API base64 endpoint
                mimetype=mimetype,
                message_key_id=message_key_id
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
