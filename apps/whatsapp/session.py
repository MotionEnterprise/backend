"""
WhatsApp Session Management

Functions for loading, saving, and querying WhatsApp sessions.
"""

import logging
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
    Stub function for triggering ComfyUI generation.
    
    This is a placeholder - actual implementation is out of scope.
    
    Args:
        session: The WhatsAppSession with all collected data
    """
    logger.info(f"Trigger generation called for {session.whatsapp_number} - STUB")
    # TODO: Implement actual ComfyUI integration
    pass
