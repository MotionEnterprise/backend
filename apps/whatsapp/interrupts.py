"""
Interrupt Handlers

Handles special commands (STOP, REDO) and new image during flow.
"""

import logging

from .evolution import send_text_message, download_image
from .session import store_image_in_gridfs, trigger_generation, load_session
from .models import ImageMeta

logger = logging.getLogger(__name__)


def handle_interrupt(session, message) -> bool:
    """
    Check if message is an interrupt command and handle it.
    
    Checks in order:
    1. STOP - cancel current flow
    2. REDO - regenerate with previous inputs
    3. New image mid-flow - store as pending
    
    Args:
        session: The WhatsAppSession
        message: The parsed IncomingMessage
        
    Returns:
        bool: True if interrupt was handled, False otherwise
    """
    # Check for STOP
    if message.type == "text":
        text_upper = message.text.strip().upper()
        
        if text_upper == "STOP":
            # Deactivate current session
            session.activeSession = False
            session.save()
            
            send_text_message(
                message.sender,
                "Flow cancelled. Send a new jewellery image to start again."
            )
            logger.info(f"Session deactivated for {message.sender}")
            return True
        
        # Check for REDO
        if text_upper == "REDO":
            if session.state == "completed":
                session.state = "generating"
                session.retry_count = 0
                send_text_message(
                    message.sender,
                    "Regenerating with your previous inputs..."
                )
                trigger_generation(session)
            else:
                send_text_message(
                    message.sender,
                    "Nothing to regenerate yet. Send a jewellery image to start."
                )
            return True
    
    # Check for new image mid-flow
    if message.type == "image":
        # States where we should NOT accept new image
        if session.state not in ("idle", "completed", "generating", "ready_for_generation"):
            # Download and store the new image
            image_bytes = download_image(message.image_url)
            if image_bytes is not None:
                try:
                    file_id = store_image_in_gridfs(
                        image_bytes,
                        message.sender,
                        message.mimetype or "image/jpeg"
                    )
                    session.pending_image = ImageMeta(
                        gridfs_file_id=file_id,
                        mimetype=message.mimetype or "image/jpeg"
                    )
                    send_text_message(
                        message.sender,
                        "You have an ongoing flow. Reply STOP to cancel and start "
                        "fresh with your new image, or continue answering the "
                        "current question."
                    )
                    logger.info(f"Pending image stored for {message.sender}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to store pending image: {str(e)}")
    
    # No interrupt matched
    return False
