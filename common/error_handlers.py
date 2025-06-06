"""
Utilidades centralizadas de manejo de errores para eliminar patrones de error redundantes.
"""
import logging
from typing import Any, Dict, Optional
from fastapi import HTTPException, status
import mysql.connector
from functools import wraps

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Manejo de errores centralizado para la aplicación."""
    
    @staticmethod
    def handle_database_error(error: Exception, operation: str = "operación de base de datos") -> HTTPException:
        """Maneja errores específicos de la base de datos."""
        logger.error(f"Error de base de datos durante {operation}: {error}")
        
        if isinstance(error, mysql.connector.Error):
            if error.errno == 1062:  # Entrada duplicada
                return HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El recurso ya existe"
                )
            elif error.errno == 1452:  # Violación de restricción de clave foránea
                return HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Violación de restricción de integridad"
                )
            else:
                return HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error de base de datos: {operation}"
                )
    
    @staticmethod
    def handle_validation_error(error: Exception, field: str = "") -> HTTPException:
        """Maneja errores de validación."""
        logger.warning(f"Error de validación en '{field}': {error}")
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error de validación{f' en {field}' if field else ''}: {str(error)}"
        )
    
    @staticmethod
    def handle_authentication_error(detail: str = "Credenciales incorrectas") -> HTTPException:
        """Maneja errores de autenticación."""
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    @staticmethod
    def handle_authorization_error(detail: str = "Acceso denegado") -> HTTPException:
        """Maneja errores de autorización."""
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


def database_error_handler(operation: str = "operación de base de datos"):
    """Decorador para manejar errores de base de datos en funciones de routers."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except mysql.connector.Error as e:
                raise ErrorHandler.handle_database_error(e, operation)
            except HTTPException:
                raise  # Volver a lanzar excepciones HTTP tal como están
            except Exception as e:
                logger.error(f"Error inesperado en {func.__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error interno durante: {operation}"
                )
        return wrapper
    return decorator


def validation_error_handler(field: str = ""):
    """Decorador para manejar errores de validación."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ValueError as e:
                raise ErrorHandler.handle_validation_error(e, field)
            except HTTPException:
                raise  # Volver a lanzar excepciones HTTP tal como están
            except Exception as e:
                logger.error(f"Error inesperado en {func.__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error interno de validación"
                )
        return wrapper
    return decorator


class BaseError(Exception):
    """
    Excepción base para errores personalizados con código HTTP y detalle.
    """
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)
