"""
Utilidades y patrones de autenticación compartidos.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import mysql.connector

from backend.auth import get_current_admin, verify_token
from backend.common.database_utils import DbDependency
from backend.common.error_handlers import ErrorHandler

# Esquema OAuth2 para autenticación por token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


class AuthDependencies:
    """Dependencias centralizadas de autenticación."""
    
    @staticmethod
    def get_current_admin_dependency():
        """Dependencia para obtener el administrador actual."""
        return Depends(get_current_admin)
    
    @staticmethod
    def get_optional_admin_dependency():
        """Dependencia opcional de administrador (para endpoints públicos con autenticación opcional)."""
        async def optional_admin(
            token: Optional[str] = Depends(oauth2_scheme),
            db: mysql.connector.connection.MySQLConnection = DbDependency
        ):
            if token:
                try:
                    return get_current_admin(token, db)
                except HTTPException:
                    return None
            return None
        return Depends(optional_admin)


class AuthValidators:
    """Utilidades comunes de validación de autenticación."""
    
    @staticmethod
    def require_admin_permissions(admin_data: dict, required_permissions: list = None):
        """Valida que el administrador tenga los permisos requeridos."""
        if not admin_data:
            raise ErrorHandler.handle_authentication_error("Se requiere autenticación de administrador")
        
        # Agregar lógica de verificación de permisos si es necesario
        # Por ahora, todos los administradores tienen todos los permisos
        return True
    
    @staticmethod
    def validate_token_format(token: str) -> bool:
        """Valida el formato del token."""
        if not token or not isinstance(token, str):
            return False
        
        # Validación básica del formato del token
        parts = token.split('.')
        return len(parts) == 3  # JWT debe tener 3 partes
    
    @staticmethod
    def is_token_expired(token_data: dict) -> bool:
        """Verificar si el token ha expirado."""
        import time
        exp = token_data.get('exp')
        if not exp:
            return True
        return time.time() > exp


# Dependencias comunes de autenticación
AdminRequired = Depends(get_current_admin)
OptionalAdmin = AuthDependencies.get_optional_admin_dependency()
