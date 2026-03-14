"""
GridFS storage utilities for the Media App.

Provides functions to save and retrieve files from MongoDB GridFS
using the Assets database connection.
"""

import logging
from typing import Optional, Dict, Any
from bson import ObjectId
from gridfs import GridFS

from core.database import get_assets_gridfs, get_assets_db_connection

logger = logging.getLogger(__name__)


def save_to_gridfs(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> ObjectId:
    """
    Save a file to GridFS in the Assets database.
    
    Args:
        file_bytes: Raw file content as bytes
        filename: Original filename (used for extension detection)
        content_type: MIME type (e.g., 'image/png', 'video/mp4')
        metadata: Optional dict of additional metadata to store with the file
        
    Returns:
        ObjectId: The GridFS file's unique ObjectId
        
    Raises:
        ValueError: If file_bytes is empty or filename is empty
        Exception: If GridFS write fails
        
    Example:
        >>> gridfs_id = save_to_gridfs(
        ...     file_bytes=image_data,
        ...     filename="output.png",
        ...     content_type="image/png",
        ...     metadata={"job_id": "123", "prompt_id": "abc"}
        ... )
        >>> print(f"Saved to GridFS: {gridfs_id}")
    """
    # Input validation
    if not file_bytes:
        raise ValueError("file_bytes cannot be empty")
    
    if not filename:
        raise ValueError("filename cannot be empty")
    
    if metadata is None:
        metadata = {}
    
    try:
        # Get GridFS instance
        gridfs = get_assets_gridfs()
        
        # Prepare metadata with content type
        file_metadata = {
            "content_type": content_type,
            "original_filename": filename,
            **metadata,
        }
        
        # Write to GridFS
        # GridFS stores files in chunks, automatically handles large files
        gridfs_id = gridfs.put(
            file_bytes,
            filename=filename,
            content_type=content_type,
            metadata=file_metadata,
        )
        
        logger.info(
            f"Saved file to GridFS: filename={filename}, "
            f"content_type={content_type}, gridfs_id={gridfs_id}"
        )
        
        return gridfs_id
        
    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(
            f"Failed to save file to GridFS: filename={filename}, error={str(e)}"
        )
        raise


def get_from_gridfs(gridfs_id: ObjectId) -> Optional[bytes]:
    """
    Retrieve a file's content from GridFS.
    
    Args:
        gridfs_id: The ObjectId of the file to retrieve
        
    Returns:
        bytes: The file content, or None if not found
        
    Example:
        >>> file_content = get_from_gridfs(ObjectId("abc123"))
        >>> if file_content:
        ...     # Process the file content
    """
    try:
        gridfs = get_assets_gridfs()
        
        # Check if file exists
        if not gridfs.exists(gridfs_id):
            logger.warning(f"GridFS file not found: {gridfs_id}")
            return None
        
        # Read file content
        gridfs_file = gridfs.get(gridfs_id)
        file_content = gridfs_file.read()
        gridfs_file.close()
        
        logger.info(f"Retrieved file from GridFS: gridfs_id={gridfs_id}")
        
        return file_content
        
    except Exception as e:
        logger.error(
            f"Failed to retrieve file from GridFS: gridfs_id={gridfs_id}, "
            f"error={str(e)}"
        )
        return None


def get_gridfs_file_info(gridfs_id: ObjectId) -> Optional[Dict[str, Any]]:
    """
    Get metadata about a GridFS file.
    
    Args:
        gridfs_id: The ObjectId of the file
        
    Returns:
        dict: File metadata including filename, content_type, metadata, 
              upload_date, or None if not found
              
    Example:
        >>> info = get_gridfs_file_info(ObjectId("abc123"))
        >>> if info:
        ...     print(f"Filename: {info['filename']}")
        ...     print(f"Content-Type: {info['content_type']}")
    """
    try:
        gridfs = get_assets_gridfs()
        
        if not gridfs.exists(gridfs_id):
            logger.warning(f"GridFS file not found: {gridfs_id}")
            return None
        
        gridfs_file = gridfs.get(gridfs_id)
        
        file_info = {
            "gridfs_id": gridfs_id,
            "filename": gridfs_file.filename,
            "content_type": gridfs_file.content_type,
            "metadata": gridfs_file.metadata,
            "upload_date": gridfs_file.upload_date,
            "length": gridfs_file.length,
        }
        
        gridfs_file.close()
        
        return file_info
        
    except Exception as e:
        logger.error(
            f"Failed to get GridFS file info: gridfs_id={gridfs_id}, "
            f"error={str(e)}"
        )
        return None


def delete_from_gridfs(gridfs_id: ObjectId) -> bool:
    """
    Delete a file from GridFS.
    
    Args:
        gridfs_id: The ObjectId of the file to delete
        
    Returns:
        bool: True if deleted, False if not found
        
    Example:
        >>> deleted = delete_from_gridfs(ObjectId("abc123"))
        >>> if deleted:
        ...     print("File deleted successfully")
    """
    try:
        gridfs = get_assets_gridfs()
        
        if not gridfs.exists(gridfs_id):
            logger.warning(f"GridFS file not found for deletion: {gridfs_id}")
            return False
        
        gridfs.delete(gridfs_id)
        
        logger.info(f"Deleted file from GridFS: gridfs_id={gridfs_id}")
        
        return True
        
    except Exception as e:
        logger.error(
            f"Failed to delete GridFS file: gridfs_id={gridfs_id}, "
            f"error={str(e)}"
        )
        return False
