"""
Funciones de autenticación y seguridad para la aplicación.
Este archivo proporciona funcionalidad para la autenticación de administradores,
gestión de tokens JWT y verificación de contraseñas.
"""

from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any
import jwt as pyjwt  # Cambiado a un alias más claro
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import mysql.connector

# Cambiado a importaciones relativas
from config import JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from database import get_db
import db_models as db_models
from db_models import SesionAdminModel
import schemas as schemas
from security_utils import get_password_hash, verify_password

# Configurar OAuth2 con JWT - corregir la URL con una barra al inicio para ruta absoluta
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

def authenticate_admin(db: mysql.connector.connection.MySQLConnection, email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Autentica a un administrador por correo y contraseña.
    """
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM administradores WHERE email = %s", 
        (email,)
    )
    admin = cursor.fetchone()
    cursor.close()
    
    if not admin:
        return None
    if not verify_password(password, admin["hashed_password"]):
        return None
    return admin

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un token JWT con los datos proporcionados.
    """
    to_encode = data.copy()
    
    expire = datetime.utcnow() + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    to_encode.update({"exp": expire})
    encoded_jwt = pyjwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def register_admin_session(
    db: mysql.connector.connection.MySQLConnection, admin_id: int, token: str, 
    ip_address: Optional[str] = None, navegador: Optional[str] = None
) -> Dict[str, Any]:
    """
    Registra una nueva sesión de administrador.
    
    Args:
        db: Conexión a la base de datos (no utilizada pero mantenida por compatibilidad).
        admin_id: ID del administrador.
        token: Token de la sesión.
        ip_address: Dirección IP.
        navegador: Información del navegador.
        
    Returns:
        Diccionario con los datos de la sesión creada.
    """
    # Calcular la fecha de expiración
    expires = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Usar SesionAdminModel para crear la sesión
    session_id = SesionAdminModel.crear(
        admin_id=admin_id,
        token=token,
        fecha_expiracion=expires,
        ip_address=ip_address,
        navegador=navegador,
        activa=True
    )
    
    # Obtener y devolver la sesión creada
    session = SesionAdminModel.obtener_por_id(session_id)
    return session

async def get_current_admin(
    token: str = Depends(oauth2_scheme), 
    db: mysql.connector.connection.MySQLConnection = Depends(get_db)
) -> Dict[str, Any]:
    """
    Obtiene el administrador actual a partir del token JWT.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodificar el token usando PyJWT
        payload = pyjwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")
        admin_id: int = payload.get("admin_id")
        
        if email is None or admin_id is None:
            raise credentials_exception
            
        token_data = schemas.TokenData(email=email, admin_id=admin_id)
    except pyjwt.PyJWTError:  # Excepción específica de PyJWT
        raise credentials_exception
    
    cursor = db.cursor(dictionary=True)
    
    # Verificar si el administrador existe y está activo
    cursor.execute(
        "SELECT * FROM administradores WHERE id = %s", 
        (token_data.admin_id,)
    )
    admin = cursor.fetchone()
    
    if admin is None or not admin["activo"]:
        cursor.close()
        raise credentials_exception
    
    # Verificar si la sesión aún es válida
    cursor.execute("""
    SELECT * FROM sesiones_admin
    WHERE admin_id = %s AND token = %s AND activa = TRUE 
    AND fecha_expiracion > %s
    """, (admin["id"], token, datetime.utcnow()))
    
    session = cursor.fetchone()
    cursor.close()
    
    if not session:
        raise credentials_exception
    
    return admin