"""
WhatsApp Session Management

Functions for loading, saving, and querying WhatsApp sessions.
"""

import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId

from mongoengine import connect
from gridfs import GridFS

from .models import WhatsAppSession, ImageMeta

logger = logging.getLogger(__name__)

# MongoDB connection aliases (these will be initialized lazily)
_dev_db = None
_assets_db = None
_gridfs = None


def _get_dev_db():
    """
    Get or initialize Dev database connection.
    """
    global _dev_db
    if _dev_db is None:
        # Connect to Dev database using environment variable
        import os
        dev_db_uri = os.environ.get("DEV_DB")
        if not dev_db_uri:
            raise ValueError("DEV_DB environment variable is required")
        
        # Ensure URI includes database name
        if "dev-db" not in dev_db_uri:
            # Add dev-db to URI if not present
            if "/" in dev_db_uri:
                base = dev_db_uri.rstrip("/")
                dev_db_uri = base + "/dev-db"
        
        connect(host=dev_db_uri, alias="dev")
        _dev_db = dev_db_uri
        logger.info(f"Connected to Dev MongoDB")
    
    return _dev_db


def _get_assets_db():
    """
    Get or initialize Assets database connection for GridFS.
    """
    global _assets_db
    if _assets_db is None:
        import os
        assets_db_uri = os.environ.get("ASSETS_DB")
        if not assets_db_uri:
            raise ValueError("ASSETS_DB environment variable is required")
        
        # Connect with alias
        connect(host=assets_db_uri, alias="assets")
        _assets_db = assets_db_uri
        logger.info("Connected to Assets MongoDB for GridFS")
    
    return _assets_db


def _get_gridfs():
    """
    Get GridFS instance for storing images.
    """
    global _gridfs
    if _gridfs is None:
        from core.database import get_assets_db_connection
        db = get_assets_db_connection()
        _gridfs = GridFS(db)
    return _gridfs


def load_session(whatsapp_number: str, create_new: bool = False) -> WhatsAppSession:
    """
    Load a WhatsApp session by phone number.
    
    If create_new=True, creates a new session document and deactivates previous ones.
    If create_new=False, finds the active session or returns new unsaved one.
    
    Args:
        whatsapp_number: The user's WhatsApp number
        create_new: If True, create new session and deactivate old ones
        
    Returns:
        WhatsAppSession: Existing or new session object
    """
    # Ensure database connection is initialized
    _get_dev_db()
    
    if create_new:
        # Deactivate all previous sessions for this number
        WhatsAppSession.objects(
            whatsapp_number=whatsapp_number,
            activeSession=True
        ).update(set__activeSession=False)
        
        # Create new session
        session = WhatsAppSession(
            whatsapp_number=whatsapp_number,
            activeSession=True
        )
        logger.info(f"Created new session for {whatsapp_number}")
        return session
    
    # Try to find active session
    session = WhatsAppSession.objects(
        whatsapp_number=whatsapp_number,
        activeSession=True
    ).first()
    
    if session is None:
        # Create new session (not saved yet)
        session = WhatsAppSession(whatsapp_number=whatsapp_number, activeSession=True)
        logger.info(f"Created new session for {whatsapp_number}")
    
    return session


def save_session(session: WhatsAppSession) -> None:
    """
    Save a WhatsApp session and update last_active timestamp.
    
    Args:
        session: The WhatsAppSession to save
    """
    session.touch()
    session.save()
    logger.debug(f"Saved session for {session.whatsapp_number}")


def complete_session(session: WhatsAppSession) -> None:
    """
    Mark a session as completed.
    Sets activeSession=False and completed_at=now.
    
    Args:
        session: The WhatsAppSession to complete
    """
    session.activeSession = False
    session.completed_at = datetime.utcnow()
    session.touch()
    session.save()
    logger.info(f"Completed session for {session.whatsapp_number}")


def get_all_jewellery_types() -> List[Dict[str, Any]]:
    """
    Get all jewellery types from constants.
    
    Returns:
        list: List of jewellery type dictionaries
    """
    from .constants import get_all_jewellery_types
    return get_all_jewellery_types()


def get_jewellery_type_by_option(option: str) -> Optional[Dict[str, Any]]:
    """
    Get jewellery type by option letter.
    
    Args:
        option: The option letter (e.g., "A", "a", "ring")
        
    Returns:
        dict or None: Jewellery type document if found
    """
    from .constants import get_jewellery_type_by_option
    return get_jewellery_type_by_option(option)


def get_prompt_document(category: str, image_type: str) -> Optional[Dict[str, Any]]:
    """
    Get prompt document by category and image_type.
    
    The prompt_id is constructed as: "{category}_{image_type}"
    e.g., "ring_plain", "necklace_human"
    
    Args:
        category: The jewellery category (e.g., "hand", "neck", "ear")
        image_type: The image type (e.g., "plain", "human", "aesthetic")
        
    Returns:
        dict or None: Prompt document if found
    """
    from core.database import get_library_collection
    
    # Construct prompt_id
    prompt_id = f"{category}-{image_type}"
    
    try:
        prompts_collection = get_library_collection("prompts")
        prompt_doc = prompts_collection.find_one({"prompt_id": prompt_id})
        return prompt_doc
    except Exception as e:
        logger.error(f"Error fetching prompt document: {str(e)}")
        return None


def store_image_in_gridfs(image_bytes: bytes, sender: str, mimetype: str) -> ObjectId:
    """
    Store an image in GridFS.
    
    Args:
        image_bytes: Raw image bytes
        sender: Sender's WhatsApp number (for filename)
        mimetype: Image MIME type
        
    Returns:
        ObjectId: The GridFS file ID
    """
    from core.database import get_assets_db_connection
    
    db = get_assets_db_connection()
    gridfs = GridFS(db)
    
    # Generate filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{sender}_{timestamp}.jpg"
    
    # Store in GridFS
    file_id = gridfs.put(
        image_bytes,
        filename=filename,
        content_type=mimetype
    )
    
    logger.info(f"Stored image in GridFS: {filename} (id: {file_id})")
    return file_id


def trigger_generation(session: WhatsAppSession) -> None:
    """
    Placeholder function for triggering image generation.
    
    This sends a placeholder image to complete the flow for testing.
    When ComfyUI is integrated, replace this entire function.
    
    Flow:
    1. Set session state to "generating"
    2. Send placeholder image to user
    3. Set session state to "completed"
    4. Send completion confirmation with REDO instructions
    
    TODO (ComfyUI Integration):
    - Replace this function with actual ComfyUI API call
    - The ComfyUI workflow should:
      1. Take session.image as input
      2. Use session.final_prompt for generation
      3. Return the generated image
    - After ComfyUI generates:
      - Send the generated image to user
      - Set session state to "completed"
      - Send completion message
    
    Args:
        session: The WhatsAppSession with all collected data
    """
    from .evolution import send_media_message, send_text_message
    from .handlers.generating import send_generation_complete_message
    
    logger.info(f"Trigger generation called for {session.whatsapp_number} - PLACEHOLDER")
    
    # Set state to generating
    session.state = "generating"
    save_session(session)
    
    # =========================================================================
    # PLACEHOLDER: Send sample image for testing
    # =========================================================================
    # TODO: Replace this with actual ComfyUI generation
    
    # Get path to placeholder image
    placeholder_image_path = os.path.join(
        os.path.dirname(__file__),
        "images",
        "gold.jpg"
    )
    
    # Check if file exists
    if os.path.exists(placeholder_image_path):
        try:
            # Send the placeholder image
            send_media_message(
                session.whatsapp_number,
                placeholder_image_path,
                f"Generated for {session.jewellery_type} - {session.image_type}"
            )
        except Exception as e:
            logger.error(f"Failed to send placeholder image: {str(e)}")
            # Fallback to text message
            send_text_message(
                session.whatsapp_number,
                f"[Placeholder] Generated image for {session.jewellery_type} ({session.image_type})"
            )
    else:
        # Fallback if image not found
        send_text_message(
            session.whatsapp_number,
            f"[Placeholder] Generated image for {session.jewellery_type} ({session.image_type})"
        )
    
    # =========================================================================
    # END PLACEHOLDER
    # =========================================================================
    
    # Mark session as completed
    session.state = "completed"
    session.completed_at = datetime.utcnow()
    session.activeSession = False
    save_session(session)
    
    # Send completion message with REDO instructions
    send_generation_complete_message(session.whatsapp_number)
    
    logger.info(f"Generation completed for {session.whatsapp_number}")
