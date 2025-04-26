"""
Utility functions for security-related operations like password hashing.
"""
import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña plana coincide con una contraseña hasheada.
    """
    # Asegurarse de que hashed_password sea bytes
    if isinstance(hashed_password, str):
        hashed_password_bytes = hashed_password.encode('utf-8')
    else:
        hashed_password_bytes = hashed_password # Asumir que ya son bytes si no es str

    # Asegurarse de que plain_password sea bytes
    plain_password_bytes = plain_password.encode('utf-8')
    
    return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)
