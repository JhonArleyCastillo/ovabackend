"""
Contact form message management router.

This router handles operations related to contact form messages including
public message submission from the frontend and administrative message
management for authenticated administrators.
"""

from typing import List, Optional, Dict, Any
import logging
from fastapi import APIRouter, Depends, HTTPException, status
import mysql.connector
import sys
import os

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import modules
from common.database_utils import DatabaseManager, DbDependency
from auth import get_current_admin
from backend.schemas import ContactoCreate, ContactoResponse, ContactoUpdate
from backend.db_models import ContactoModel
from backend.common.router_utils import handle_errors
from pydantic import BaseModel, EmailStr

# Configure module logger
logger = logging.getLogger(__name__)

# Configure contact router with proper prefix and metadata
router = APIRouter(
    prefix="/api/contactos",
    tags=["contacto"],
    responses={404: {"description": "Contact message not found"}},
)

@router.post("/", response_model=ContactoResponse, 
            status_code=status.HTTP_201_CREATED)
@handle_errors
async def enviar_mensaje(
    contacto: ContactoCreate,
    db: mysql.connector.connection.MySQLConnection = DbDependency
) -> ContactoResponse:
    """
    Submit a message from the public contact form.
    
    This endpoint is public and does not require authentication.
    It creates a new contact message in the database for later
    review by administrators.
    
    Args:
        contacto (ContactoCreate): Contact form data including name,
                                  email, subject, and message.
        db (mysql.connector.connection.MySQLConnection): Database connection.
    
    Returns:
        ContactoResponse: Created contact message data.
        
    Raises:
        HTTPException: If message creation fails.
    """
    try:
        # Use ContactoModel to create and retrieve the record
        contacto_id = ContactoModel.crear(
            contacto.nombre_completo,
            contacto.email,
            contacto.asunto,
            contacto.mensaje
        )
        
        # Retrieve the created contact record
        nuevo_contacto = ContactoModel.obtener_por_id(contacto_id)
        
        if not nuevo_contacto:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Error creating contact message"
            )
            
        return nuevo_contacto
        
    except Exception as e:
        logger.error(f"Error creating contact message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit contact message"
        )

@router.get("/", response_model=List[ContactoResponse])
@handle_errors
async def listar_mensajes(
    skip: int = 0,
    limit: int = 100,
    solo_no_leidos: bool = False,
    db: mysql.connector.connection.MySQLConnection = DbDependency,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Lista todos los mensajes de contacto.
    Solo disponible para administradores.
    """
    # Obtener mensajes con opción de filtrar no leídos
    where = " WHERE leido = FALSE" if solo_no_leidos else ""
    query = f"SELECT * FROM contactos{where} LIMIT %s OFFSET %s"
    return DatabaseManager.execute_query(db, query, (limit, skip), fetch_all=True)

@router.get("/{contacto_id}", response_model=ContactoResponse)
@handle_errors
async def obtener_mensaje(
    contacto_id: int,
    db: mysql.connector.connection.MySQLConnection = DbDependency,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Obtiene un mensaje de contacto por su ID.
    Solo disponible para administradores.
    """
    mensaje = ContactoModel.obtener_por_id(contacto_id)
    
    if mensaje is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mensaje no encontrado"
        )
        
    return mensaje

@router.patch("/{contacto_id}", response_model=ContactoResponse)
@handle_errors
async def actualizar_mensaje(
    contacto_id: int,
    datos: ContactoUpdate,
    db: mysql.connector.connection.MySQLConnection = DbDependency,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Actualiza el estado de un mensaje de contacto.
    Solo disponible para administradores.
    """
    # Verificar que el mensaje existe
    mensaje = ContactoModel.obtener_por_id(contacto_id)
    
    if mensaje is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mensaje no encontrado"
        )
    
    # Actualizar campos según lo enviado
    if datos.leido is not None:
        ContactoModel.marcar_como_leido(contacto_id, datos.leido)
        
    if datos.respondido is not None:
        ContactoModel.marcar_como_respondido(contacto_id, datos.respondido)
    
    # Obtener el mensaje actualizado
    mensaje_actualizado = ContactoModel.obtener_por_id(contacto_id)
    return mensaje_actualizado

@router.delete("/{contacto_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_errors
async def eliminar_mensaje(
    contacto_id: int,
    db: mysql.connector.connection.MySQLConnection = DbDependency,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Elimina un mensaje de contacto.
    Solo disponible para administradores.
    """
    # Verificar que el mensaje existe
    mensaje = ContactoModel.obtener_por_id(contacto_id)
    
    if mensaje is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mensaje no encontrado"
        )
    
    # Eliminar el mensaje
    eliminado = ContactoModel.eliminar(contacto_id)
     
    if not eliminado:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar el mensaje"
        )
        
class UsuarioContactGroup(BaseModel):
    email: EmailStr
    mensajes: List[ContactoResponse]
@router.get("/agrupados", response_model=List[UsuarioContactGroup])
@handle_errors
async def listar_contactos_agrupados(
    db:mysql.connector.connection.MySQLConnection = DbDependency
):
    todos = DatabaseManager.execute_query(
        db, 
        "SELECT nombre, email, asunto, mensaje, fecha_envio, leido, respondido FROM contactos",
        fetch_all=True
    )
    
    grupos: Dict[str, List[dict]] = {}
    for c in todos:
        grupos.setdefault(c['email'], []).append(c)
    
    return [{"email": email, "mensajes": msgs} for email, msgs in grupos.items()]