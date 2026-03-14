"""
Interrupt Handlers

Handles special commands (STOP, REDO) and new image during flow.
"""

import logging

from .evolution import send_text_message, download_image
from .session import store_image_in_supabase, save_session
from .handlers.redo import send_redo_choice_message
from .models import ImageMeta
from apps.media.supabase_storage import UPLOADED_MEDIA_BUCKET

logger = logging.getLogger(__name__)


def handle_interrupt(session, message) -> bool:
    """
    Check if message is an interrupt command and handle it.
    
    Checks in order:
    1. STOP - cancel current flow
    2. REDO - ask user for choice (same or change)
    3. New image mid-flow - store as pending
    
    The session passed here should already be the correct one
    (either active session or most recent completed session).
    
    Args:
        session: The WhatsAppSession (should already be found correctly)
        message: The parsed IncomingMessage
        
    Returns:
        bool: True if interrupt was handled, False otherwise
    """
    # Check for STOP
    if message.type == "text":
        text_upper = message.text.strip().upper()
        
        if text_upper == "STOP":
            if session and session.activeSession:
                session.activeSession = False
                save_session(session)
            
            send_text_message(
                message.sender,
                "Flow cancelled. Send a new jewellery image to start again."
            )
            logger.info(f"STOP command processed for {message.sender}")
            return True
        
        # Check for REDO
        if text_upper == "REDO":
            # Session should already be the right one (found in views.py)
            # Just verify it's a valid state for REDO
            if session and (session.state == "completed" or session.state == "generating"):
                # Mark state as awaiting redo choice
                session.state = "awaiting_redo_choice"
                session.activeSession = True  # Reactivate for redo flow
                save_session(session)
                
                # Ask user for choice
                send_redo_choice_message(message.sender)
                
                logger.info(f"REDO choice asked for {message.sender}")
                return True
            elif session is None:
                # No session found - tell user to start fresh
                send_text_message(
                    message.sender,
                    "Nothing to regenerate yet. Send a jewellery image to start."
                )
                return True
            else:
                # Session exists but not in completed/generating state
                send_text_message(
                    message.sender,
                    "Nothing to regenerate yet. Send a jewellery image to start."
                )
                return True
    
    # Check for new image mid-flow
    if message.type == "image" and session:
        # States where we should NOT accept new image
        if session.state not in ("idle", "completed", "generating", "ready_for_generation", "awaiting_redo_choice"):
            # Download and store the new image (pass message_key_id to get base64 from Evolution API)
            image_bytes = download_image(message.image_url, message.message_key_id)
            if image_bytes is not None:
                try:
                    file_path = store_image_in_supabase(
                        image_bytes,
                        message.sender,
                        message.mimetype or "image/jpeg"
                    )
                    session.pending_image = ImageMeta(
                        file_path=file_path,
                        bucket_name=UPLOADED_MEDIA_BUCKET,
                        mimetype=message.mimetype or "image/jpeg"
                    )
                    save_session(session)
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
    
    # For completed state receiving image - let router handle it
    if session and session.state == "completed" and message.type == "image":
        # Don't handle here, let router handle starting new session
        return False
    
    # No interrupt matched
    return False
