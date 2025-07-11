"""
Administrator service module for CRUD operations and authentication.

This module provides functions for creating, reading, updating, and deleting
administrator accounts, as well as authentication-related operations.
"""
from typing import List, Dict, Any, Optional
import mysql.connector
from fastapi import HTTPException, status
import sys
import os

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import modules
from common.database_utils import DatabaseManager
from schemas import AdminCreate
from security_utils import get_password_hash
from auth import authenticate_admin as auth_authenticate_admin


def create_admin(
    db: mysql.connector.connection.MySQLConnection, 
    admin_data: AdminCreate
) -> Dict[str, Any]:
    """
    Create a new administrator in the database.
    
    Args:
        db (mysql.connector.connection.MySQLConnection): Database connection.
        admin_data (AdminCreate): Administrator data from request.
    
    Returns:
        Dict[str, Any]: Created administrator data.
        
    Raises:
        HTTPException: If email already exists or creation fails.
    """
    # Check if email already exists to prevent duplicates
    existing = DatabaseManager.execute_query(
        db,
        "SELECT * FROM administradores WHERE email = %s",
        (admin_data.email,),
        fetch_one=True
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado"
        )

    # Hash password for secure storage
    hashed_password = get_password_hash(admin_data.password)
    
    # Insert new administrator into database
    new_admin_id = DatabaseManager.execute_query(
        db,
        """INSERT INTO administradores 
           (email, nombre, hashed_password, es_superadmin, activo) 
           VALUES (%s, %s, %s, %s, %s)""",
        (admin_data.email, admin_data.nombre, hashed_password, False, True),
        commit=True
    )
    
    # Retrieve and return the created administrator
    new_admin = DatabaseManager.execute_query(
        db,
        "SELECT * FROM administradores WHERE id = %s",
        (new_admin_id,),
        fetch_one=True
    )
    return new_admin


def list_admins(
    db: mysql.connector.connection.MySQLConnection,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Lista administradores con paginación.
    """
    return DatabaseManager.execute_query(
        db,
        "SELECT * FROM administradores LIMIT %s OFFSET %s",
        (limit, skip),
        fetch_all=True
    )


def authenticate_admin(
    db: mysql.connector.connection.MySQLConnection, 
    email: str, 
    password: str
) -> Dict[str, Any]:
    """
    Autentica a un administrador.
    """
    return auth_authenticate_admin(db, email, password)


def update_admin(
    db: mysql.connector.connection.MySQLConnection,
    admin_id: int,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Actualiza un administrador con los campos proporcionados.
    """
    # Construir dinámicamente la consulta UPDATE
    fields = []
    params: List[Any] = []
    for key, value in data.items():
        fields.append(f"{key} = %s")
        params.append(value)
    params.append(admin_id)

    query = f"UPDATE administradores SET {', '.join(fields)} WHERE id = %s"
    DatabaseManager.execute_query(
        db,
        query,
        tuple(params),
        commit=True
    )
    # Devolver el administrador actualizado
    return DatabaseManager.execute_query(
        db,
        "SELECT * FROM administradores WHERE id = %s",
        (admin_id,),
        fetch_one=True
    )
