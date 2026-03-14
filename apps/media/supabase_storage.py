"""
Supabase Storage utilities for the Media App.

Provides functions to save and retrieve files from Supabase Storage
buckets using the configured SUPABASE_URL and SUPABASE_KEY.
"""

import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any
from io import BytesIO

logger = logging.getLogger(__name__)

# Bucket names
UPLOADED_MEDIA_BUCKET = "uploaded-media"
GENERATED_MEDIA_BUCKET = "generated-media"

# Supabase client singleton
_supabase_client = None


def _get_supabase_client():
    """
    Get or create Supabase client instance.
    
    Returns:
        Client: Supabase client instance
        
    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY not configured
    """
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    from supabase import create_client
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    if not supabase_url:
        raise ValueError("SUPABASE_URL environment variable is required")
    if not supabase_key:
        raise ValueError("SUPABASE_KEY environment variable is required")
    
    _supabase_client = create_client(supabase_url, supabase_key)
    logger.info("Supabase client initialized")
    
    return _supabase_client


def _get_file_path(phone_number: str, filename: str, is_generated: bool = False) -> str:
    """
    Generate the file path for Supabase storage.
    
    Format: {phone_number}/{timestamp}_{original_filename}
    For generated: {phone_number}/generated_{timestamp}.png
    
    Args:
        phone_number: User's WhatsApp number
        filename: Original filename
        is_generated: If True, use generated_ prefix
        
    Returns:
        str: File path for Supabase
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    if is_generated:
        # For generated images, use .png extension
        ext = "png"
        return f"{phone_number}/generated_{timestamp}.{ext}"
    else:
        # For uploaded images, preserve extension
        return f"{phone_number}/{timestamp}_{filename}"


def save_to_supabase(
    file_bytes: bytes,
    phone_number: str,
    filename: str,
    bucket_name: str,
    is_generated: bool = False,
) -> str:
    """
    Save a file to Supabase Storage.
    
    Args:
        file_bytes: Raw file content as bytes
        phone_number: User's WhatsApp number (for folder organization)
        filename: Original filename (used for extension detection)
        bucket_name: Supabase bucket name (e.g., 'uploaded-media', 'generated-media')
        is_generated: If True, use generated_ prefix for filename
        
    Returns:
        str: The file path in Supabase (not the full URL)
        
    Raises:
        ValueError: If file_bytes is empty or filename is empty
        Exception: If Supabase upload fails
    """
    if not file_bytes:
        raise ValueError("file_bytes cannot be empty")
    
    if not filename:
        raise ValueError("filename cannot be empty")
    
    try:
        client = _get_supabase_client()
        
        # Generate file path
        file_path = _get_file_path(phone_number, filename, is_generated)
        
        # Upload file
        response = client.storage.from_(bucket_name).upload(
            path=file_path,
            file=file_bytes,
            file_options={
                "content-type": _get_content_type(filename),
            }
        )
        
        logger.info(
            f"Saved file to Supabase: bucket={bucket_name}, path={file_path}"
        )
        
        return file_path
        
    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(
            f"Failed to save file to Supabase: bucket={bucket_name}, "
            f"filename={filename}, error={str(e)}"
        )
        raise


def get_public_url(bucket_name: str, file_path: str) -> str:
    """
    Get the public URL for a file in Supabase Storage.
    
    Args:
        bucket_name: Supabase bucket name
        file_path: The file path in the bucket
        
    Returns:
        str: Public URL for the file
    """
    client = _get_supabase_client()
    return client.storage.from_(bucket_name).get_public_url(file_path)


def get_from_supabase(bucket_name: str, file_path: str) -> Optional[bytes]:
    """
    Retrieve a file's content from Supabase Storage.
    
    Args:
        bucket_name: Supabase bucket name
        file_path: The file path in the bucket
        
    Returns:
        bytes: The file content, or None if not found
    """
    try:
        client = _get_supabase_client()
        
        # Download the file
        response = client.storage.from_(bucket_name).download(file_path)
        
        logger.info(f"Retrieved file from Supabase: bucket={bucket_name}, path={file_path}")
        
        return response
        
    except Exception as e:
        logger.error(
            f"Failed to retrieve file from Supabase: bucket={bucket_name}, "
            f"path={file_path}, error={str(e)}"
        )
        return None


def delete_from_supabase(bucket_name: str, file_path: str) -> bool:
    """
    Delete a file from Supabase Storage.
    
    Args:
        bucket_name: Supabase bucket name
        file_path: The file path in the bucket
        
    Returns:
        bool: True if deleted, False if not found or on error
    """
    try:
        client = _get_supabase_client()
        
        client.storage.from_(bucket_name).remove([file_path])
        
        logger.info(f"Deleted file from Supabase: bucket={bucket_name}, path={file_path}")
        
        return True
        
    except Exception as e:
        logger.error(
            f"Failed to delete file from Supabase: bucket={bucket_name}, "
            f"path={file_path}, error={str(e)}"
        )
        return False


def get_file_info(bucket_name: str, file_path: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata about a file in Supabase Storage.
    
    Args:
        bucket_name: Supabase bucket name
        file_path: The file path in the bucket
        
    Returns:
        dict: File metadata or None if not found
    """
    try:
        client = _get_supabase_client()
        
        # List files to get info (Supabase doesn't have direct file info API)
        response = client.storage.from_(bucket_name).list(
            path=file_path.rsplit("/", 1)[0] if "/" in file_path else "",
            search=file_path.split("/")[-1] if "/" in file_path else file_path
        )
        
        for file_info in response:
            if file_info.get("name") == file_path.split("/")[-1]:
                return {
                    "file_path": file_path,
                    "name": file_info.get("name"),
                    "size": file_info.get("size"),
                    "created_at": file_info.get("created_at"),
                }
        
        logger.warning(f"File not found in Supabase: bucket={bucket_name}, path={file_path}")
        return None
        
    except Exception as e:
        logger.error(
            f"Failed to get file info from Supabase: bucket={bucket_name}, "
            f"path={file_path}, error={str(e)}"
        )
        return None


def _get_content_type(filename: str) -> str:
    """
    Get MIME type from filename extension.
    
    Args:
        filename: The filename to get content type for
        
    Returns:
        str: MIME type string
    """
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    
    content_types = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "gif": "image/gif",
        "mp4": "video/mp4",
        "webm": "video/webm",
    }
    
    return content_types.get(ext, "application/octet-stream")


# =============================================================================
# Convenience functions matching GridFS API (for backward compatibility)
# =============================================================================

def save_uploaded_image(
    file_bytes: bytes,
    phone_number: str,
    filename: str,
    content_type: str,
) -> str:
    """
    Save a user-uploaded image to Supabase.
    
    Convenience function for storing images from WhatsApp uploads.
    Uses the 'uploaded-media' bucket.
    
    Args:
        file_bytes: Raw image bytes
        phone_number: User's WhatsApp number
        filename: Original filename
        content_type: MIME type
        
    Returns:
        str: File path in Supabase
    """
    return save_to_supabase(
        file_bytes=file_bytes,
        phone_number=phone_number,
        filename=filename,
        bucket_name=UPLOADED_MEDIA_BUCKET,
        is_generated=False,
    )


def save_generated_image(
    file_bytes: bytes,
    phone_number: str,
    content_type: str = "image/png",
) -> str:
    """
    Save a ComfyUI-generated image to Supabase.
    
    Convenience function for storing generated images.
    Uses the 'generated-media' bucket.
    
    Args:
        file_bytes: Raw image bytes
        phone_number: User's WhatsApp number
        content_type: MIME type (default: image/png)
        
    Returns:
        str: File path in Supabase
    """
    return save_to_supabase(
        file_bytes=file_bytes,
        phone_number=phone_number,
        filename="generated.png",
        bucket_name=GENERATED_MEDIA_BUCKET,
        is_generated=True,
    )


def get_uploaded_image(file_path: str) -> Optional[bytes]:
    """
    Retrieve a user-uploaded image from Supabase.
    
    Args:
        file_path: The file path in the uploaded-media bucket
        
    Returns:
        bytes: The image content, or None if not found
    """
    return get_from_supabase(UPLOADED_MEDIA_BUCKET, file_path)


def get_generated_image(file_path: str) -> Optional[bytes]:
    """
    Retrieve a generated image from Supabase.
    
    Args:
        file_path: The file path in the generated-media bucket
        
    Returns:
        bytes: The image content, or None if not found
    """
    return get_from_supabase(GENERATED_MEDIA_BUCKET, file_path)


def delete_uploaded_image(file_path: str) -> bool:
    """
    Delete a user-uploaded image from Supabase.
    
    Args:
        file_path: The file path in the uploaded-media bucket
        
    Returns:
        bool: True if deleted successfully
    """
    return delete_from_supabase(UPLOADED_MEDIA_BUCKET, file_path)


def delete_generated_image(file_path: str) -> bool:
    """
    Delete a generated image from Supabase.
    
    Args:
        file_path: The file path in the generated-media bucket
        
    Returns:
        bool: True if deleted successfully
    """
    return delete_from_supabase(GENERATED_MEDIA_BUCKET, file_path)


def get_uploaded_image_url(file_path: str) -> str:
    """
    Get public URL for an uploaded image.
    
    Args:
        file_path: The file path in the uploaded-media bucket
        
    Returns:
        str: Public URL for the image
    """
    return get_public_url(UPLOADED_MEDIA_BUCKET, file_path)


def get_generated_image_url(file_path: str) -> str:
    """
    Get public URL for a generated image.
    
    Args:
        file_path: The file path in the generated-media bucket
        
    Returns:
        str: Public URL for the image
    """
    return get_public_url(GENERATED_MEDIA_BUCKET, file_path)
