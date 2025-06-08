"""
Rutas API para la autenticación y gestión de administradores.

Este archivo define los endpoints para el inicio de sesión de administradores,
la gestión de sus cuentas y el seguimiento de sesiones.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
import mysql.connector
import sys
import os

# Añadir el directorio raíz del proyecto al path de Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Ahora importamos desde backend con rutas absolutas
from backend.common.database_utils import DatabaseManager, DbDependency  # Uso centralizado de DB
from backend.common.router_utils import handle_errors  # Importar el decorador
from backend.common.service_utils import extract_client_info
from backend.common.auth_utils import build_token_response
from backend.services.admin_service import create_admin as service_create_admin, list_admins as service_list_admins, authenticate_admin as service_authenticate_admin
from backend.common.router_utils import require_superadmin
import backend.auth as auth
import backend.schemas as schemas
import backend.db_models as db_models

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
):
    """
    Autentica un administrador y genera un token JWT.
    """
    admin = service_authenticate_admin(db, form_data.username, form_data.password)
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