"""
Utility functions for security-related operations like password hashing.
"""
from passlib import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña plana coincide con una contraseña hasheada.
    """
    # passlib.hash.bcrypt maneja internamente la conversión y verificación
    try:
        return bcrypt.verify(plain_password, hashed_password)
    except Exception:
        # Si hay cualquier error (formato incompatible, etc.), devolver False
        return False
