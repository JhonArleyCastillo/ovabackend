"""
Refactored usuarios router using consolidated utilities.
This demonstrates the elimination of code redundancy.
"""

from typing import List
from fastapi import status
import mysql.connector

# Consolidated imports - no more sys.path manipulation needed
from backend.common.router_utils import RouterFactory, CommonResponses, CRUDBase
from backend.common.database_utils import DatabaseManager, DbDependency
from backend.common.auth_utils import AdminRequired
from backend.common.error_handlers import database_error_handler, validation_error_handler
import backend.schemas as schemas


# Crear router usando la fábrica
router = RouterFactory.create_router(
    prefix="/api/usuarios",
    tags=["usuarios"]
)

# Manejador de operaciones CRUD
usuarios_crud = CRUDBase("usuarios")


@router.post("/", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
@database_error_handler("registro de usuario")
@validation_error_handler("datos de usuario")
def registrar_usuario(
    usuario: schemas.UsuarioCreate, 
    db: mysql.connector.connection.MySQLConnection = DbDependency
):
    """
    Registra un nuevo usuario con su correo electrónico.
    """
    # Verificar si el usuario ya existe
    existing_user = DatabaseManager.execute_query(
        db,
        "SELECT * FROM usuarios WHERE email = %s",
        (usuario.email,),
        fetch_one=True
    )
    
    if existing_user:
        # If user exists but is inactive, reactivate them
        if not existing_user["activo"]:
            usuarios_crud.update(db, existing_user["id"], {"activo": 1})
            return usuarios_crud.get_by_id(db, existing_user["id"])
        
        # User is already active
        raise CommonResponses.bad_request("El correo electrónico ya está registrado")
    
    # Crear nuevo usuario
    user_data = {
        "email": usuario.email,
        "nombre": usuario.nombre,
        "activo": 1
    }
    
    new_user_id = usuarios_crud.create(db, user_data)
    return usuarios_crud.get_by_id(db, new_user_id)


@router.get("/", response_model=List[schemas.UsuarioResponse])
@database_error_handler("obtención de usuarios")
def obtener_usuarios(
    skip: int = 0, 
    limit: int = 100, 
    db: mysql.connector.connection.MySQLConnection = DbDependency,
    current_admin: dict = AdminRequired
):
    """
    Obtiene la lista de usuarios registrados.
    Requiere autenticación como administrador.
    """
    return usuarios_crud.get_all(db, limit=limit, offset=skip)


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
@database_error_handler("desactivación de usuario")
def desactivar_usuario(
    usuario_id: int, 
    db: mysql.connector.connection.MySQLConnection = DbDependency,
    current_admin: dict = AdminRequired
):
    """
    Desactiva un usuario por su ID.
    Requiere autenticación como administrador.
    """
    # Verificar si el usuario existe
    usuario = usuarios_crud.get_by_id(db, usuario_id)
    if not usuario:
        raise CommonResponses.not_found("Usuario no encontrado")
    
    # Deactivate user
    usuarios_crud.update(db, usuario_id, {"activo": 0})
    return None
