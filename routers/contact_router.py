"""
Router para gestionar mensajes del formulario de contacto.

Este router maneja las operaciones relacionadas con los mensajes de contacto:
- Envío de mensajes desde el frontend
- Listado y gestión de mensajes para administradores
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
import mysql.connector
from backend.common.database_utils import DatabaseManager, DbDependency
from backend.auth import get_current_admin
import schemas
from backend.db_models import ContactoModel
from backend.common.router_utils import handle_errors
import backend.db_models as db_models

router = APIRouter(
    prefix="/api/contacto",
    tags=["contacto"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.ContactoResponse, status_code=status.HTTP_201_CREATED)
@handle_errors
async def enviar_mensaje(
    contacto: schemas.ContactoCreate,
    db: mysql.connector.connection.MySQLConnection = DbDependency
):
    """
    Envía un mensaje desde el formulario de contacto.
    Esta ruta es pública y no requiere autenticación.
    """
    # Crear el mensaje en la base de datos
    contacto_id = DatabaseManager.execute_query(
        db,
        "INSERT INTO contacto (nombre, email, asunto, mensaje) VALUES (%s, %s, %s, %s)",
        (contacto.nombre, contacto.email, contacto.asunto, contacto.mensaje),
        commit=True,
        fetch_one=False
    )
        
    # Obtener el mensaje creado
    nuevo_contacto = DatabaseManager.execute_query(
        db,
        "SELECT * FROM contacto WHERE id = %s",
        (contacto_id,),
        fetch_one=True
    )
    if not nuevo_contacto:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear el mensaje de contacto")
    return nuevo_contacto

@router.get("/", response_model=List[schemas.ContactoResponse])
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
    query = f"SELECT * FROM contacto{where} LIMIT %s OFFSET %s"
    return DatabaseManager.execute_query(db, query, (limit, skip), fetch_all=True)

@router.get("/{contacto_id}", response_model=schemas.ContactoResponse)
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

@router.patch("/{contacto_id}", response_model=schemas.ContactoResponse)
@handle_errors
async def actualizar_mensaje(
    contacto_id: int,
    datos: schemas.ContactoUpdate,
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