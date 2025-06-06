"""
Servicio de administradores: operaciones CRUD y autenticación.
"""
from typing import List, Dict, Any
import mysql.connector
from fastapi import HTTPException, status

from backend.common.database_utils import DatabaseManager
from backend.schemas import AdminCreate
from backend.security_utils import get_password_hash
from backend.auth import authenticate_admin as auth_authenticate_admin


def create_admin(
    db: mysql.connector.connection.MySQLConnection, 
    admin_data: AdminCreate
) -> Dict[str, Any]:
    """
    Crea un nuevo administrador en la base de datos.
    """
    # Verificar si el correo ya existe
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

    hashed_password = get_password_hash(admin_data.password)
    new_admin_id = DatabaseManager.execute_query(
        db,
        "INSERT INTO administradores (email, nombre, hashed_password, es_superadmin, activo) VALUES (%s, %s, %s, %s, %s)",
        (admin_data.email, admin_data.nombre, hashed_password, False, True),
        commit=True
    )
    # Obtener el administrador creado
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
