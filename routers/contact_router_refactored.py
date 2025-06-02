"""
Refactored contact router using consolidated utilities.
"""

from typing import List, Optional
from fastapi import status

# Consolidated imports - no more manual path/import management
from backend.common.imports import schemas
from backend.common.router_utils import RouterFactory, CommonResponses
from backend.common.database_utils import DbDependency
from backend.common.auth_utils import AdminRequired
from backend.common.error_handlers import database_error_handler, validation_error_handler
from backend.db_models import ContactoModel


# Crear router usando la fábrica
router = RouterFactory.create_router(
    prefix="/api/contacto",
    tags=["contacto"]
)


@router.post("/", response_model=schemas.ContactoResponse, status_code=status.HTTP_201_CREATED)
@database_error_handler("envío de mensaje de contacto")
@validation_error_handler("datos de contacto")
async def enviar_mensaje(
    contacto: schemas.ContactoCreate,
    db = DbDependency
):
    """
    Envía un mensaje desde el formulario de contacto.
    Esta ruta es pública y no requiere autenticación.
    """
    # Crear mensaje de contacto
    contacto_id = ContactoModel.crear(
        nombre=contacto.nombre,
        email=contacto.email,
        asunto=contacto.asunto,
        mensaje=contacto.mensaje
    )
    
    # Obtener mensaje creado
    nuevo_contacto = ContactoModel.obtener_por_id(contacto_id)
    
    if nuevo_contacto is None:
        raise CommonResponses.server_error("Error al crear el mensaje de contacto")
        
    return nuevo_contacto


@router.get("/", response_model=List[schemas.ContactoResponse])
@database_error_handler("listado de mensajes")
async def listar_mensajes(
    skip: int = 0,
    limit: int = 100,
    solo_no_leidos: bool = False,
    db = DbDependency,
    current_admin: dict = AdminRequired
):
    """
    Lista todos los mensajes de contacto.
    Solo disponible para administradores.
    """
    return ContactoModel.listar(
        skip=skip, 
        limit=limit, 
        solo_no_leidos=solo_no_leidos
    )


@router.get("/{contacto_id}", response_model=schemas.ContactoResponse)
@database_error_handler("obtención de mensaje")
async def obtener_mensaje(
    contacto_id: int,
    db = DbDependency,
    current_admin: dict = AdminRequired
):
    """
    Obtiene un mensaje específico por ID.
    Solo disponible para administradores.
    """
    mensaje = ContactoModel.obtener_por_id(contacto_id)
    
    if mensaje is None:
        raise CommonResponses.not_found("Mensaje no encontrado")
        
    return mensaje


@router.patch("/{contacto_id}", response_model=schemas.ContactoResponse)
@database_error_handler("actualización de mensaje")
async def marcar_como_leido(
    contacto_id: int,
    db = DbDependency,
    current_admin: dict = AdminRequired
):
    """
    Marca un mensaje como leído.
    Solo disponible para administradores.
    """
    # Verificar si el mensaje existe
    mensaje = ContactoModel.obtener_por_id(contacto_id)
    if mensaje is None:
        raise CommonResponses.not_found("Mensaje no encontrado")
    
    # Actualizar estado del mensaje
    ContactoModel.actualizar(contacto_id, {"leido": True})
    
    # Devolver mensaje actualizado
    return ContactoModel.obtener_por_id(contacto_id)


@router.delete("/{contacto_id}", status_code=status.HTTP_204_NO_CONTENT)
@database_error_handler("eliminación de mensaje")
async def eliminar_mensaje(
    contacto_id: int,
    db = DbDependency,
    current_admin: dict = AdminRequired
):
    """
    Elimina un mensaje de contacto.
    Solo disponible para administradores.
    """
    # Verificar si el mensaje existe
    mensaje = ContactoModel.obtener_por_id(contacto_id)
    if mensaje is None:
        raise CommonResponses.not_found("Mensaje no encontrado")
    
    # Eliminar mensaje
    ContactoModel.eliminar(contacto_id)
    return None
