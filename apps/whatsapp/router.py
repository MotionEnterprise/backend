"""
Session Router

Routes messages to appropriate handlers based on session state.
"""

import logging

from .evolution import send_text_message
from .handlers import (
    handle_idle,
    handle_jewellery_type,
    handle_image_type,
    handle_dynamic,
    handle_generating,
)

logger = logging.getLogger(__name__)


def route(session, message) -> None:
    """
    Route message to appropriate handler based on session state.
    
    States:
    - idle: User needs to send an image
    - awaiting_jewellery_type: User needs to select jewellery type
    - awaiting_image_type: User needs to select image type
    - awaiting_dynamic: User needs to answer dynamic questions
    - generating: Image is being generated
    - completed: User has completed the flow
    
    Args:
        session: The WhatsAppSession
        message: The parsed IncomingMessage
    """
    state = session.state
    
    if state == "idle":
        handle_idle(session, message)
    
    elif state == "awaiting_jewellery_type":
        handle_jewellery_type(session, message)
    
    elif state == "awaiting_image_type":
        handle_image_type(session, message)
    
    elif state == "awaiting_dynamic":
        handle_dynamic(session, message)
    
    elif state == "generating":
        handle_generating(session, message)
    
    elif state == "completed":
        handle_completed(session, message)
    
    elif state == "ready_for_generation":
        # Treat same as completed
        handle_completed(session, message)
    
    else:
        # Unknown state - reset and start fresh
        logger.warning(f"Unknown state '{state}' for {message.sender}, resetting")
        session.reset()
        send_text_message(
            message.sender,
            "Something went wrong. Please send a jewellery image to start fresh."
        )


def handle_completed(session, message) -> None:
    """
    Handle messages when session is in completed state.
    
    Args:
        session: The WhatsAppSession
        message: The parsed IncomingMessage
    """
    if message.type == "image":
        # Start new flow with new image
        session.state = "idle"
        handle_idle(session, message)
    else:
        # Tell user to start fresh or regenerate
        send_text_message(
            message.sender,
            "Send a new jewellery image to start. Reply REDO to regenerate."
        )
