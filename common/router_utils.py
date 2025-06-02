"""
Utilidades y patrones compartidos para routers para eliminar redundancia entre routers.
"""
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
import mysql.connector
import logging

from backend.common.database_utils import DatabaseManager, DbDependency

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
        
        return DatabaseManager.execute_query(db, query, params, fetch_all=True) or []
    
    def create(
        self,
        db: mysql.connector.connection.MySQLConnection,
        data: Dict
    ) -> int:
        """Crear un nuevo registro y devolver su ID."""
        fields = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        query = f"INSERT INTO {self.table_name} ({fields}) VALUES ({placeholders})"
        
        with DatabaseManager.get_cursor(db, dictionary=False) as cursor:
            cursor.execute(query, tuple(data.values()))
            db.commit()
            return cursor.lastrowid
    
    def update(
        self,
        db: mysql.connector.connection.MySQLConnection,
        record_id: int,
        data: Dict
    ) -> bool:
        """Actualizar un registro por ID."""
        set_clause = ", ".join([f"{key} = %s" for key in data.keys()])
        query = f"UPDATE {self.table_name} SET {set_clause} WHERE {self.id_field} = %s"
        params = tuple(data.values()) + (record_id,)
        
        DatabaseManager.execute_query(db, query, params, commit=True)
        return True
    
    def delete(
        self,
        db: mysql.connector.connection.MySQLConnection,
        record_id: int
    ) -> bool:
        """Eliminar un registro por ID."""
        query = f"DELETE FROM {self.table_name} WHERE {self.id_field} = %s"
        DatabaseManager.execute_query(db, query, (record_id,), commit=True)
        return True
