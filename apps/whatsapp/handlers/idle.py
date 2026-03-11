"""
Idle State Handler

Handles the initial state when a user sends an image.
"""

import logging

from ..evolution import send_text_message, download_image
from ..session import store_image_in_gridfs, get_all_jewellery_types, load_session
from ..constants import build_jewellery_options_text
from ..models import ImageMeta

logger = logging.getLogger(__name__)


def handle_idle(session, message) -> None:
    """
    Handle messages in the idle state.
    
    Expected: User sends an image to start the flow.
    
    Args:
        session: The WhatsAppSession
        message: The parsed IncomingMessage
    """
    # Only accept images in idle state
    if message.type != "image":
        send_text_message(
            message.sender,
            "Please send a jewellery image to get started."
        )
        return
    
    # Download the image
    image_bytes = download_image(message.image_url)
    if image_bytes is None:
        send_text_message(
            message.sender,
            "Sorry, couldn't process your image. Try again."
        )
        return
    
    # Store in GridFS
    try:
        file_id = store_image_in_gridfs(
            image_bytes,
            message.sender,
            message.mimetype or "image/jpeg"
        )
    except Exception as e:
        logger.error(f"Failed to store image in GridFS: {str(e)}")
        send_text_message(
            message.sender,
            "Sorry, couldn't process your image. Try again."
        )
        return
    
    # Create new session (this will deactivate previous sessions)
    # Note: session passed in might be old, so we create fresh one
    session = load_session(message.sender, create_new=True)
    
    # Update session
    session.image = ImageMeta(
        gridfs_file_id=file_id,
        mimetype=message.mimetype or "image/jpeg"
    )
    session.state = "awaiting_jewellery_type"
    session.activeSession = True
    
    # Build and send Q1
    jewellery_types = get_all_jewellery_types()
    options_text = build_jewellery_options_text()
    
    send_text_message(
        message.sender,
        f"What type of jewellery is this?\n\n{options_text}"
    )
    
    logger.info(f"Sent jewellery type question to {message.sender}")
