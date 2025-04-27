"""
Utility functions for security-related operations like password hashing.
"""

import hashlib
import secrets

# Constant salt prefix - se puede cambiar por uno más seguro y personalizado
SALT_PREFIX = "OVASecureSalt_"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña plana coincide con una contraseña hasheada.
    """
    # El formato de la contraseña hasheada es: salt:hash
    if ":" not in hashed_password:
        return False
        
    salt, stored_hash = hashed_password.split(":", 1)
    # Calcular el hash de la contraseña plana con la misma sal
    computed_hash = hashlib.sha256((salt + plain_password).encode()).hexdigest()
    
    # Comparar el hash calculado con el almacenado
    return secrets.compare_digest(computed_hash, stored_hash)

def get_password_hash(password: str) -> str:
    """
    Genera un hash seguro para una contraseña dada.
    Retorna el hash como una cadena de texto en formato salt:hash
    """
    # Generar una sal única para esta contraseña
    salt = SALT_PREFIX + secrets.token_hex(8)
    
    # Generar el hash SHA-256 de la combinación de sal y contraseña
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    
    # Devolver la combinación de sal y hash separados por dos puntos
    return f"{salt}:{hashed}"
