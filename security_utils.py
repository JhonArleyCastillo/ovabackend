"""
Utilidades de seguridad para manejo de contraseñas.

Este módulo maneja todo lo relacionado con hashing y verificación de contraseñas
usando bcrypt, que es el estándar de oro para almacenar contraseñas de forma segura.

Como desarrollador fullstack, nunca guardes contraseñas en texto plano.
Siempre usa estas funciones para hashear antes de guardar en BD y verificar en login.
"""

import bcrypt
import logging
from typing import Union

# Logger para este módulo
logger = logging.getLogger(__name__)

def get_password_hash(password: str) -> str:
    """
    Genera un hash seguro para una contraseña en texto plano usando bcrypt.
    
    Esta función toma una contraseña como "mipassword123" y la convierte
    en algo como "$2b$12$xyz..." que es seguro para guardar en la BD.
    
    Bcrypt automáticamente genera un "salt" único cada vez, así que la misma
    contraseña produce hashes diferentes cada vez (¡eso es bueno!).
    
    Args:
        password: Contraseña en texto plano que quieres hashear
        
    Returns:
        str: Hash bcrypt como string UTF-8 listo para guardar en BD
        
    Raises:
        ValueError: Si la contraseña está vacía o no es válida
        RuntimeError: Si falla la operación de hashing
    """
    if not password or not isinstance(password, str):
        raise ValueError("La contraseña debe ser un string no vacío")
        
    try:
        password_bytes = password.encode('utf-8')
        # Generamos salt y hasheamos con bcrypt
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Error hasheando contraseña: {str(e)}")
        raise RuntimeError(f"Falló el hashing de contraseña: {str(e)}")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con su hash bcrypt.
    
    Esta función es la que usas en el login: tomas la contraseña que escribió
    el usuario y la comparas contra el hash que tienes guardado en la BD.
    
    Si retorna True = login correcto, False = contraseña incorrecta.
    
    Args:
        plain_password: Contraseña en texto plano (lo que escribió el usuario)
        hashed_password: Hash bcrypt guardado en la BD
        
    Returns:
        bool: True si la contraseña coincide, False si no
        
    Raises:
        ValueError: Si alguno de los parámetros es inválido
    """
    if not plain_password or not hashed_password:
        raise ValueError("Ambas contraseñas deben ser strings no vacíos")
        
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        
        # Usamos bcrypt para verificar contraseña contra hash
        return bcrypt.checkpw(password_bytes, hashed_bytes)
        
    except Exception as e:
        logger.error(f"Error verificando contraseña: {str(e)}")
        return False  # En caso de error, mejor rechazar el login