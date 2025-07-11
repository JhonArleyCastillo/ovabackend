"""
Authentication and administrator management API routes.

This module defines API endpoints for administrator login, account management,
and session tracking with comprehensive error handling and security features.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
import mysql.connector
import sys
import os

# Add project root directory to Python path for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import modules
from common.database_utils import DatabaseManager, DbDependency
from common.router_utils import handle_errors
from common.service_utils import extract_client_info
from common.auth_utils import build_token_response
from services.admin_service import (
    create_admin as service_create_admin, 
    list_admins as service_list_admins, 
    authenticate_admin as service_authenticate_admin, 
    update_admin as service_update_admin
)
from common.router_utils import require_superadmin
import auth
import schemas
import db_models

# Configure router with proper prefix and metadata
router = APIRouter(
    prefix="/api/auth",
    tags=["autenticación"],
    responses={404: {"description": "Recurso no encontrado"}}
)

@router.post("/token", response_model=schemas.Token)
@handle_errors
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: mysql.connector.connection.MySQLConnection = DbDependency,
    request: Request = None
) -> Dict[str, Any]:
    """
    Authenticate an administrator and generate a JWT token.
    
    This endpoint validates administrator credentials and creates a new
    session with proper token generation and security tracking.
    
    Args:
        form_data (OAuth2PasswordRequestForm): Login credentials from form.
        db (mysql.connector.connection.MySQLConnection): Database connection.
        request (Request): HTTP request object for client info extraction.
    
    Returns:
        Dict[str, Any]: Token response with access token and metadata.
        
    Raises:
        HTTPException: If credentials are invalid or authentication fails.
    """
    # Authenticate administrator using service layer
    admin = service_authenticate_admin(
        db, 
        form_data.username, 
        form_data.password
    )
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = {
        "sub": admin["email"],
        "admin_id": admin["id"]
    }
    
    access_token = auth.create_access_token(token_data)
    
    # Obtener información del cliente
    client_info = extract_client_info(request)
    # Registrar la sesión
    auth.register_admin_session(
        db=db,
        admin_id=admin["id"],
        token=access_token,
        ip_address=client_info["ip_address"],
        navegador=client_info["user_agent"]
    )
    return build_token_response(
        access_token,
        admin["es_superadmin"],
        admin["id"],
        admin["email"],
        admin["nombre"]
    )

@router.post("/admins/", response_model=schemas.AdminResponse)
@handle_errors
@require_superadmin
async def crear_admin(
    admin: schemas.AdminCreate,
    db: mysql.connector.connection.MySQLConnection = DbDependency
):
    """
    Crea un nuevo administrador (requiere superadmin).
    """
    return service_create_admin(db, admin)

@router.get("/admins/", response_model=List[schemas.AdminResponse])
@handle_errors
@require_superadmin
async def listar_admins(
    skip: int = 0,
    limit: int = 100,
    db: mysql.connector.connection.MySQLConnection = DbDependency
):
    """
    Lista todos los administradores (requiere superadmin).
    """
    return service_list_admins(db, skip, limit)

@router.get("/sessions/", response_model=List[schemas.SesionAdminResponse])
@handle_errors # Aplicar decorador
async def listar_sesiones(
    db: mysql.connector.connection.MySQLConnection = DbDependency,
    current_admin: dict = Depends(auth.get_current_admin)
):
    """
    Lista las sesiones activas del administrador actual.
    """
    # Obtener sesiones activas del administrador
    return DatabaseManager.execute_query(
        db,
        "SELECT * FROM sesiones_admin WHERE admin_id = %s AND activa = TRUE",
        (current_admin["id"],),
        fetch_all=True
    )

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@handle_errors # Aplicar decorador
async def cerrar_sesion(
    token: str = Depends(auth.oauth2_scheme),
    db: mysql.connector.connection.MySQLConnection = DbDependency,
    current_admin: dict = Depends(auth.get_current_admin)
):
    """
    Cierra la sesión actual del administrador.
    """
    # Cerrar la sesión actual en la base de datos
    DatabaseManager.execute_query(
        db,
        "UPDATE sesiones_admin SET activa = FALSE WHERE admin_id = %s AND token = %s AND activa = TRUE",
        (current_admin["id"], token),
        commit=True
    )
    return None

@router.patch("/admins/{admin_id}", response_model=schemas.AdminResponse)
@handle_errors
@require_superadmin
async def modificar_admin(
    admin_id: int,
    cambios: schemas.AdminUpdate,
    db: mysql.connector.connection.MySQLConnection = DbDependency
):
    """
    Modifica campos de un administrador (requiere superadmin).
    """
    datos = cambios.dict(exclude_none=True)
    return service_update_admin(db, admin_id, datos)

@router.post("/admins/{admin_id}/toggle", response_model=schemas.AdminResponse)
@handle_errors
@require_superadmin
async def activar_desactivar_admin(
    admin_id: int,
    action: str,
    db: mysql.connector.connection.MySQLConnection = DbDependency
):
    """
    Activa o desactiva un administrador. action debe ser 'activar' o 'desactivar'.
    """
    if action not in ("activar", "desactivar"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Acción inválida")
    estado = True if action == "activar" else False
    return service_update_admin(db, admin_id, {"activo": estado})