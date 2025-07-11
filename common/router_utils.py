"""
Utilidades y patrones compartidos para routers para eliminar redundancia entre routers.
"""
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
import mysql.connector
import logging
from functools import wraps
import sys
import os

# Add the parent directory to sys.path to allow imports  
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.database_utils import DatabaseManager, DbDependency
from common.error_handlers import BaseError  # Ensure BaseError exists and is your base class

logger = logging.getLogger(__name__)


class RouterFactory:
    """Fábrica para crear routers estandarizados con patrones comunes."""
    
    @staticmethod
    def create_router(
        prefix: str,
        tags: List[str],
        additional_responses: Optional[Dict] = None
    ) -> APIRouter:
        """Crear un APIRouter estandarizado con configuración común."""
        responses = {404: {"description": "Recurso no encontrado"}}
        if additional_responses:
            responses.update(additional_responses)
            
        return APIRouter(
            prefix=prefix,
            tags=tags,
            responses=responses
        )


class CommonResponses:
    """Respuestas HTTP estandarizadas."""
    
    @staticmethod
    def not_found(detail: str = "Recurso no encontrado"):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )
    
    @staticmethod
    def bad_request(detail: str = "Solicitud incorrecta"):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
    
    @staticmethod
    def unauthorized(detail: str = "No autorizado"):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    @staticmethod
    def forbidden(detail: str = "Acceso denegado"):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )
    
    @staticmethod
    def server_error(detail: str = "Error interno del servidor"):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class CRUDBase:
    """Clase base para operaciones CRUD comunes."""
    
    def __init__(self, table_name: str, id_field: str = "id"):
        self.table_name = table_name
        self.id_field = id_field
    
    def get_by_id(
        self,
        db: mysql.connector.connection.MySQLConnection,
        record_id: int
    ) -> Optional[Dict]:
        """Obtener un registro por ID."""
        query = f"SELECT * FROM {self.table_name} WHERE {self.id_field} = %s"
        return DatabaseManager.execute_query(db, query, (record_id,), fetch_one=True)
    
    def get_all(
        self,
        db: mysql.connector.connection.MySQLConnection,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict]:
        """Obtener todos los registros con paginación opcional."""
        query = f"SELECT * FROM {self.table_name}"
        params = ()
        
        if limit is not None:
            query += " LIMIT %s"
            params += (limit,)
        if offset is not None:
            query += " OFFSET %s"
            params += (offset,)
            
        return DatabaseManager.execute_query(db, query, params, fetch_all=True)

    # Aquí puedes añadir métodos para create, update, delete si son genéricos
    # Por ejemplo:
    # def create(self, db: mysql.connector.connection.MySQLConnection, data: Dict) -> int:
    #     fields = \", \".join(data.keys())
    #     placeholders = \", \".join([\"%s\"] * len(data))
    #     query = f\"INSERT INTO {self.table_name} ({fields}) VALUES ({placeholders})\"
    #     return DatabaseManager.execute_query(db, query, tuple(data.values()), commit=True, get_last_id=True)


# Decorador para manejo de errores

def handle_errors(fn):
    """
    Decorador para manejar errores comunes y convertirlos en HTTPException.
    Asume que los errores personalizados heredan de BaseError y tienen
    atributos `status_code` y `detail`.
    """
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except BaseError as e:
            # Si el error ya tiene status_code y detail definidos (como en BaseError)
            logger.error(f"Error controlado en {fn.__name__}: {e.detail} (Status: {e.status_code})")
            raise HTTPException(status_code=e.status_code, detail=e.detail)
        except HTTPException as e:
            # Re-lanzar HTTPExceptions existentes, loggeando si es un error de servidor
            if e.status_code >= 500:
                logger.error(f"HTTPException no controlada (servidor) en {fn.__name__}: {e.detail} (Status: {e.status_code})")
            else:
                logger.warning(f"HTTPException (cliente) en {fn.__name__}: {e.detail} (Status: {e.status_code})")
            raise
        except mysql.connector.Error as db_err:
            # Manejo específico para errores de base de datos
            logger.error(f"Error de base de datos en {fn.__name__}: {db_err}")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Error de base de datos: {db_err.msg}")
        except Exception as e:
            # Para cualquier otra excepción no controlada, retornar un 500 genérico
            logger.exception(f"Error no esperado en {fn.__name__}: {e}") # Usar logger.exception para incluir traceback
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")
    return wrapper

# Decorador para requerir superadmin en endpoints críticos
from fastapi import HTTPException, status

def require_superadmin(fn):
    """
    Decorador para asegurar que el administrador actual es superadmin.
    """
    @wraps(fn)
    async def wrapper(*args, current_admin=Depends(lambda: None), **kwargs):
        # current_admin se inyecta con Depends(get_current_admin)
        if not current_admin or not current_admin.get("es_superadmin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso restringido: requiere superadmin"
            )
        return await fn(*args, **kwargs)
    return wrapper
