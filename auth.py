"""
Funciones de autenticación y seguridad para la aplicación.

Este módulo proporciona funcionalidad para la autenticación de administradores,
gestión de tokens JWT y verificación de contraseñas.
"""

from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any
from jose import jwt, JWTError  # JWT library for token management
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import mysql.connector

# Import relative configuration and utilities
from config import (
    JWT_SECRET_KEY, 
    JWT_ALGORITHM, 
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from database import get_db
import db_models
from db_models import SesionAdminModel
import schemas
from security_utils import get_password_hash, verify_password

# OAuth2 scheme configuration with absolute URL path
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

def authenticate_admin(
    db: mysql.connector.connection.MySQLConnection, 
    email: str, 
    password: str
) -> Optional[Dict[str, Any]]:
    """
    Authenticate an administrator by email and password.
    
    Args:
        db (mysql.connector.connection.MySQLConnection): Database connection.
        email (str): Administrator's email address.
        password (str): Plain text password to verify.
    
    Returns:
        Optional[Dict[str, Any]]: Administrator data if authentication 
                                  successful, None otherwise.
    
    Raises:
        mysql.connector.Error: If database query fails.
    """
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM administradores WHERE email = %s", 
            (email,)
        )
        admin = cursor.fetchone()
        
        if not admin:
            return None
        
        if not verify_password(password, admin["hashed_password"]):
            return None
            
        return admin
    except mysql.connector.Error as e:
        # Log error in production environment
        print(f"Database error during authentication: {e}")
        return None
    finally:
        cursor.close()

def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token with the provided data.
    
    Args:
        data (Dict[str, Any]): Token payload data to encode.
        expires_delta (Optional[timedelta]): Custom expiration time. 
                                           Uses default if None.
    
    Returns:
        str: Encoded JWT token.
    
    Raises:
        ValueError: If token encoding fails.
    """
    to_encode = data.copy()
    
    # Calculate expiration time
    expire = datetime.utcnow() + (
        expires_delta if expires_delta 
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(
            to_encode, 
            JWT_SECRET_KEY, 
            algorithm=JWT_ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        raise ValueError(f"Failed to encode JWT token: {e}")

def register_admin_session(
    db: mysql.connector.connection.MySQLConnection, 
    admin_id: int, 
    token: str, 
    ip_address: Optional[str] = None, 
    navegador: Optional[str] = None
) -> Dict[str, Any]:
    """
    Register a new administrator session in the database.
    
    Args:
        db (mysql.connector.connection.MySQLConnection): Database connection
                                                         (maintained for 
                                                         compatibility).
        admin_id (int): Administrator's unique identifier.
        token (str): Session token.
        ip_address (Optional[str]): Client's IP address.
        navegador (Optional[str]): Browser information.
        
    Returns:
        Dict[str, Any]: Created session data.
        
    Raises:
        DatabaseError: If session creation fails.
    """
    # Calculate expiration time based on token lifetime
    expires = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    
    # Use SesionAdminModel to create session in database
    session_id = SesionAdminModel.crear(
        admin_id=admin_id,
        token=token,
        fecha_expiracion=expires,
        ip_address=ip_address,
        navegador=navegador,
        activa=True
    )
    
    # Retrieve and return the created session
    session = SesionAdminModel.obtener_por_id(session_id)
    return session

async def get_current_admin(
    token: str = Depends(oauth2_scheme), 
    db: mysql.connector.connection.MySQLConnection = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current administrator from JWT token.
    
    Args:
        token (str): JWT token from request header.
        db (mysql.connector.connection.MySQLConnection): Database connection.
    
    Returns:
        Dict[str, Any]: Current administrator data.
        
    Raises:
        HTTPException: If token is invalid, expired, or admin not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token to extract payload
        payload = jwt.decode(
            token, 
            JWT_SECRET_KEY, 
            algorithms=[JWT_ALGORITHM]
        )
        email: str = payload.get("sub")
        admin_id: int = payload.get("admin_id")
        
        # Validate required token data
        if email is None or admin_id is None:
            raise credentials_exception
            
        token_data = schemas.TokenData(email=email, admin_id=admin_id)
        
    except JWTError:
        raise credentials_exception
    
    cursor = db.cursor(dictionary=True)
    
    try:
        # Verify administrator exists and is active
        cursor.execute(
            "SELECT * FROM administradores WHERE id = %s", 
            (token_data.admin_id,)
        )
        admin = cursor.fetchone()
        
        if admin is None or not admin["activo"]:
            raise credentials_exception
        
        # Verify session is still valid
        cursor.execute("""
        SELECT * FROM sesiones_admin
        WHERE admin_id = %s AND token = %s AND activa = TRUE 
        AND fecha_expiracion > %s
        """, (admin["id"], token, datetime.utcnow()))
        
        session = cursor.fetchone()
        
        if not session:
            raise credentials_exception
        
        return admin
        
    except mysql.connector.Error as e:
        # Log database error in production
        print(f"Database error in get_current_admin: {e}")
        raise credentials_exception
    finally:
        cursor.close()