"""
Router para manejo de mensajes del formulario de contacto.

Este router maneja todo lo relacionado con mensajes de contacto:
- Recepción de mensajes desde el frontend (endpoint público)
- Gestión administrativa de mensajes (endpoints protegidos)

Como desarrollador fullstack, aquí están los endpoints que usa el formulario
de contacto del frontend y el panel admin para revisar los mensajes.
"""

from typing import List, Optional, Dict, Any
import logging
from fastapi import APIRouter, Depends, HTTPException, status
import mysql.connector
import sys
import os

# Agregamos el directorio padre para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importamos módulos necesarios
try:
    from ..common.database_utils import DatabaseManager, DbDependency
    from ..auth import get_current_admin
    from ..schemas import ContactoCreate, ContactoResponse, ContactoUpdate
    from ..db_models import ContactoModel
    from ..common.router_utils import handle_errors
except ImportError:
    from common.database_utils import DatabaseManager, DbDependency
    from auth import get_current_admin
    from schemas import ContactoCreate, ContactoResponse, ContactoUpdate
    from db_models import ContactoModel
    from common.router_utils import handle_errors
from pydantic import BaseModel, EmailStr

# Logger para este módulo
logger = logging.getLogger(__name__)

# Configuramos el router con metadata apropiada
router = APIRouter(
    prefix="/api/contactos",
    tags=["contacto"],
    responses={404: {"description": "Mensaje de contacto no encontrado"}},
)

@router.post("/", response_model=ContactoResponse, 
            status_code=status.HTTP_201_CREATED)
@handle_errors
async def enviar_mensaje(
    contacto: ContactoCreate,
    db: mysql.connector.connection.MySQLConnection = DbDependency
) -> ContactoResponse:
    """
    Recibe un mensaje desde el formulario de contacto público.
    
    Este endpoint NO requiere autenticación - cualquiera puede enviar mensajes.
    Los mensajes se guardan en BD para que los administradores los revisen después.
    
    Es el endpoint que usa el frontend cuando alguien llena el formulario de contacto.
    
    Args:
        contacto: Datos del formulario (nombre, email, asunto, mensaje)
        db: Conexión a la BD (se inyecta automáticamente)
    
    Returns:
        ContactoResponse: Datos del mensaje creado (con ID y fecha)
        
    Raises:
        HTTPException: Si falla la creación del mensaje
    """
    try:
        # Usamos el modelo para crear el registro en BD
        contacto_id = ContactoModel.crear(
            contacto.nombre_completo,
            contacto.email,
            contacto.asunto,
            contacto.mensaje
        )
        
        # Recuperamos el contacto recién creado para devolverlo
        nuevo_contacto = ContactoModel.obtener_por_id(contacto_id)
        
        if not nuevo_contacto:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Error creando mensaje de contacto"
            )
            
        return nuevo_contacto
        
    except Exception as e:
        logger.error(f"Error creando mensaje de contacto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falló el envío del mensaje de contacto"
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