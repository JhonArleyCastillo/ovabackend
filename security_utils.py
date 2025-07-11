"""
Security utilities for the application.

This module provides functions for password hashing and verification using
the bcrypt library for secure password storage and authentication.
"""

import bcrypt
import logging
from typing import Union

# Configure module-level logger
logger = logging.getLogger(__name__)

def get_password_hash(password: str) -> str:
    """
    Generate a secure hash for a plaintext password using bcrypt.
    
    Args:
        password (str): Plaintext password to hash.
        
    Returns:
        str: Bcrypt hashed password as a UTF-8 string.
        
    Raises:
        ValueError: If password is empty or invalid.
        RuntimeError: If hashing operation fails.
    """
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string")
        
    try:
        password_bytes = password.encode('utf-8')
        # Generate salt and hash password using bcrypt
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Error hashing password: {str(e)}")
        raise RuntimeError(f"Password hashing failed: {str(e)}")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify if a plaintext password matches its bcrypt hash.
    
    Args:
        plain_password (str): Plaintext password to verify.
        hashed_password (str): Bcrypt hash to compare against.
        
    Returns:
        bool: True if password matches hash, False otherwise.
        
    Raises:
        ValueError: If either password parameter is invalid.
    """
    if not plain_password or not hashed_password:
        raise ValueError("Both passwords must be non-empty strings")
        
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        
        # Use bcrypt to verify password against hash
        return bcrypt.checkpw(password_bytes, hashed_bytes)
        
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        return False