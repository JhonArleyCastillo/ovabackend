"""
Utilidades y patrones de base de datos compartidos para eliminar redundancia entre routers.
"""
from typing import Generator, Optional, Dict, Any
from fastapi import Depends, HTTPException, status
import mysql.connector
import logging
from contextlib import contextmanager
import sys
import os

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import database module
try:
    from ..database import get_db  # when imported as package
except ImportError:
    from database import get_db  # fallback when sys.path was altered

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Administrador centralizado de operaciones de base de datos."""
    
    @staticmethod
    def get_db_dependency():
        """Dependencia de base de datos estandarizada para routers."""
        return Depends(get_db)
    @staticmethod
    @contextmanager
    def get_cursor(db: mysql.connector.connection.MySQLConnection, dictionary: bool = True):
        """Administrador de contexto para operaciones de cursor de base de datos."""
        cursor = db.cursor(dictionary=dictionary)
        try:
            yield cursor
        except Exception as e:
            logger.error(f"Error en operación de base de datos: {e}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Falló la operación de base de datos"
            )
        finally:
            cursor.close()
    @staticmethod
    def execute_query(
        db: mysql.connector.connection.MySQLConnection,
        query: str,
        params: tuple = (),
        fetch_one: bool = False,
        fetch_all: bool = False,
        commit: bool = False
    ) -> Optional[Any]:
        """
        Ejecución estandarizada de consultas con manejo de errores.
        
        Args:
            db: Conexión a la base de datos
            query: Cadena de consulta SQL
            params: Tupla de parámetros de consulta
            fetch_one: Si obtener un resultado
            fetch_all: Si obtener todos los resultados
            commit: Si confirmar la transacción
            
        Returns:
            Resultado de la consulta o None
        """
        with DatabaseManager.get_cursor(db) as cursor:
            cursor.execute(query, params)
            
            result = None
            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
            
            if commit:
                db.commit()
                
            return result
    @staticmethod
    def check_record_exists(
        db: mysql.connector.connection.MySQLConnection,
        table: str,
        field: str,
        value: Any
    ) -> bool:
        """Verifica si un registro existe en la base de datos."""
        query = f"SELECT 1 FROM {table} WHERE {field} = %s LIMIT 1"
        result = DatabaseManager.execute_query(db, query, (value,), fetch_one=True)
        return result is not None


# Dependencia común de base de datos
DbDependency = Depends(get_db)
