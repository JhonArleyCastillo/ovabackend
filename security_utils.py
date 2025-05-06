"""
Utilidades de seguridad para la aplicación.
Este archivo proporciona funciones para el hash y verificación de contraseñas.
"""

import bcrypt
import logging

logger = logging.getLogger(__name__)

def get_password_hash(password: str) -> str:
    """
    Genera un hash para una contraseña.
    
    Args:
        password: Contraseña en texto plano.
        
    Returns:
        Hash de la contraseña.
    """
    password_bytes = password.encode('utf-8')
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano corresponde a un hash.
    
    Args:
        plain_password: Contraseña en texto plano.
        hashed_password: Hash de la contraseña.
        
    Returns:
        True si la contraseña es correcta, False en caso contrario.
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Error al verificar contraseña: {str(e)}")
        return False