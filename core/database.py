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
