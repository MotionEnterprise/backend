"""
Core database utilities for MongoDB connections.
Provides shared connection functions for all apps to access different databases.
"""

import os
import logging
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from gridfs import GridFS

# Configure logging
logger = logging.getLogger(__name__)

# Global client instances
_library_client: Optional[MongoClient] = None
_library_db: Optional[Database] = None


def get_library_db_connection() -> Database:
    """
    Get or create MongoDB connection for the Library database.
    
    Reads connection string from LIBRARY_DB environment variable.
    Connection is cached globally to avoid creating multiple connections.
    
    Returns:
        Database: The Library database instance
        
    Raises:
        ValueError: If LIBRARY_DB environment variable is not set
        ConnectionFailure: If unable to connect to MongoDB
    """
    global _library_client, _library_db
    
    # Return cached connection if available
    if _library_db is not None:
        return _library_db
    
    # Get connection string from environment
    library_db_uri = os.environ.get('LIBRARY_DB')
    
    if not library_db_uri:
        logger.error("LIBRARY_DB environment variable not set")
        raise ValueError("LIBRARY_DB environment variable is required")
    
    try:
        logger.info("Connecting to Library MongoDB database...")
        _library_client = MongoClient(library_db_uri)
        
        # Extract database name from URI or use default
        # URI format: mongodb+srv://user:pass@host/dbname
        # If no database specified, use 'library' as default
        uri_parts = library_db_uri.split('@')
        if len(uri_parts) > 1:
            after_host = uri_parts[-1]
            if '/' in after_host:
                db_name = after_host.split('/')[1].split('?')[0]
                if not db_name:
                    db_name = 'library'
            else:
                db_name = 'library'
        else:
            db_name = 'library'
        
        _library_db = _library_client[db_name]
        
        # Test connection
        _library_client.admin.command('ping')
        logger.info(f"Successfully connected to Library database: {db_name}")
        
        return _library_db
        
    except Exception as e:
        logger.error(f"Failed to connect to Library database: {str(e)}")
        raise


def get_library_collection(collection_name: str) -> Collection:
    """
    Get a specific collection from the Library database.
    
    Args:
        collection_name: Name of the collection to access
        
    Returns:
        Collection: The specified collection instance
    """
    db = get_library_db_connection()
    return db[collection_name]


def close_library_connection() -> None:
    """
    Close the Library MongoDB connection.
    Should be called during application shutdown.
    """
    global _library_client, _library_db
    
    if _library_client is not None:
        logger.info("Closing Library MongoDB connection...")
        _library_client.close()
        _library_client = None
        _library_db = None
        logger.info("Library MongoDB connection closed")


# Connection health check for monitoring
def check_library_connection() -> bool:
    """
    Check if Library database connection is alive.
    
    Returns:
        bool: True if connection is healthy, False otherwise
    """
    try:
        if _library_client is not None:
            _library_client.admin.command('ping')
            return True
        return False
    except Exception:
        return False


# =============================================================================
# Dev Database Connection (dev-db for WhatsApp sessions)
# =============================================================================

# Global client instances for Dev database
_dev_client: Optional[MongoClient] = None
_dev_db: Optional[Database] = None


def get_dev_db_connection() -> Database:
    """
    Get or create MongoDB connection for the Dev database.
    This database stores WhatsApp sessions.
    
    Reads connection string from DEV_DB environment variable.
    Connection is cached globally to avoid creating multiple connections.
    
    Returns:
        Database: The Dev database instance
        
    Raises:
        ValueError: If DEV_DB environment variable is not set
        ConnectionFailure: If unable to connect to MongoDB
    """
    global _dev_client, _dev_db
    
    # Return cached connection if available
    if _dev_db is not None:
        return _dev_db
    
    # Get connection string from environment
    dev_db_uri = os.environ.get('DEV_DB')
    
    if not dev_db_uri:
        logger.error("DEV_DB environment variable not set")
        raise ValueError("DEV_DB environment variable is required")
    
    try:
        logger.info("Connecting to Dev MongoDB database...")
        _dev_client = MongoClient(dev_db_uri)
        
        # Extract database name from URI or use 'dev-db' as default
        uri_parts = dev_db_uri.split('@')
        if len(uri_parts) > 1:
            after_host = uri_parts[-1]
            if '/' in after_host:
                db_name = after_host.split('/')[1].split('?')[0]
                if not db_name:
                    db_name = 'dev-db'
            else:
                db_name = 'dev-db'
        else:
            db_name = 'dev-db'
        
        _dev_db = _dev_client[db_name]
        
        # Test connection
        _dev_client.admin.command('ping')
        logger.info(f"Successfully connected to Dev database: {db_name}")
        
        return _dev_db
        
    except Exception as e:
        logger.error(f"Failed to connect to Dev database: {str(e)}")
        raise


def get_dev_collection(collection_name: str) -> Collection:
    """
    Get a specific collection from the Dev database.
    
    Args:
        collection_name: Name of the collection to access
        
    Returns:
        Collection: The specified collection instance
    """
    db = get_dev_db_connection()
    return db[collection_name]


def close_dev_connection() -> None:
    """
    Close the Dev MongoDB connection.
    Should be called during application shutdown.
    """
    global _dev_client, _dev_db
    
    if _dev_client is not None:
        logger.info("Closing Dev MongoDB connection...")
        _dev_client.close()
        _dev_client = None
        _dev_db = None
        logger.info("Dev MongoDB connection closed")


def check_dev_connection() -> bool:
    """
    Check if Dev database connection is alive.
    
    Returns:
        bool: True if connection is healthy, False otherwise
    """
    try:
        if _dev_client is not None:
            _dev_client.admin.command('ping')
            return True
        return False
    except Exception:
        return False


# =============================================================================
# Assets Database Connection (GridFS for images)
# =============================================================================

# Global client instances for Assets
_assets_client: Optional[MongoClient] = None
_assets_db: Optional[Database] = None


def get_assets_db_connection() -> Database:
    """
    Get or create MongoDB connection for the Assets database.
    This database is used for GridFS image storage.
    
    Reads connection string from ASSETS_DB environment variable.
    Connection is cached globally to avoid creating multiple connections.
    
    Returns:
        Database: The Assets database instance
        
    Raises:
        ValueError: If ASSETS_DB environment variable is not set
        ConnectionFailure: If unable to connect to MongoDB
    """
    global _assets_client, _assets_db
    
    # Return cached connection if available
    if _assets_db is not None:
        return _assets_db
    
    # Get connection string from environment
    assets_db_uri = os.environ.get('ASSETS_DB')
    
    if not assets_db_uri:
        logger.error("ASSETS_DB environment variable not set")
        raise ValueError("ASSETS_DB environment variable is required")
    
    try:
        logger.info("Connecting to Assets MongoDB database...")
        _assets_client = MongoClient(assets_db_uri)
        
        # Extract database name from URI or use 'assets' as default
        # The URI format includes appName, extract database name
        uri_parts = assets_db_uri.split('@')
        if len(uri_parts) > 1:
            after_host = uri_parts[-1]
            if '/' in after_host:
                db_name = after_host.split('/')[1].split('?')[0]
                if not db_name:
                    db_name = 'assets'
            else:
                db_name = 'assets'
        else:
            db_name = 'assets'
        
        _assets_db = _assets_client[db_name]
        
        # Test connection
        _assets_client.admin.command('ping')
        logger.info(f"Successfully connected to Assets database: {db_name}")
        
        return _assets_db
        
    except Exception as e:
        logger.error(f"Failed to connect to Assets database: {str(e)}")
        raise


def get_assets_gridfs() -> GridFS:
    """
    Get GridFS instance for the Assets database.
    
    Returns:
        GridFS: GridFS instance for file storage
    """
    db = get_assets_db_connection()
    return GridFS(db)


def close_assets_connection() -> None:
    """
    Close the Assets MongoDB connection.
    Should be called during application shutdown.
    """
    global _assets_client, _assets_db
    
    if _assets_client is not None:
        logger.info("Closing Assets MongoDB connection...")
        _assets_client.close()
        _assets_client = None
        _assets_db = None
        logger.info("Assets MongoDB connection closed")


def check_assets_connection() -> bool:
    """
    Check if Assets database connection is alive.
    
    Returns:
        bool: True if connection is healthy, False otherwise
    """
    try:
        if _assets_client is not None:
            _assets_client.admin.command('ping')
            return True
        return False
    except Exception:
        return False
