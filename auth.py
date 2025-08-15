"""
Sistema de autenticación y seguridad para administradores.

Este módulo maneja todo lo relacionado con login de administradores:
- Autenticación con email y password
- Generación y validación de tokens JWT
- Middleware de seguridad para endpoints protegidos

Como desarrollador fullstack, este es el corazón de la seguridad del admin panel.
Si hay problemas de login o tokens expirados, aquí es donde buscar.
"""

from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any
from jose import jwt, JWTError  # Librería JWT para manejo de tokens
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import mysql.connector

# Importamos configuración
from config import (
    JWT_SECRET_KEY, 
    JWT_ALGORITHM, 
    ACCESS_TOKEN_EXPIRE_MINUTES
)
try:
    from .database import get_db
except ImportError:
    from database import get_db
import db_models
from db_models import SesionAdminModel
import schemas
from security_utils import get_password_hash, verify_password

# Configuración OAuth2 - esto le dice a FastAPI dónde está el endpoint de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

def authenticate_admin(
    db: mysql.connector.connection.MySQLConnection, 
    email: str, 
    password: str
) -> Optional[Dict[str, Any]]:
    """
    Autentica un administrador por email y contraseña.
    
    Esta función es la que realmente verifica si el login es correcto.
    Busca el admin por email y verifica que la contraseña coincida.
    
    Args:
        db: Conexión a la base de datos
        email: Email del administrador
        password: Contraseña en texto plano (se verifica contra el hash)
    
    Returns:
        Dict con datos del admin si el login es correcto, None si falla
    
    Raises:
        mysql.connector.Error: Si hay problemas con la BD
    """
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM administradores WHERE email = %s", 
            (email,)
        )
        admin = cursor.fetchone()
        
        if not admin:
            return None  # Email no existe
        
        if not verify_password(password, admin["hashed_password"]):
            return None  # Contraseña incorrecta
            
        return admin  # ¡Login exitoso!
    except mysql.connector.Error as e:
        # En producción deberías loggear esto apropiadamente
        print(f"Error de BD durante autenticación: {e}")
        return None
    finally:
        cursor.close()

def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crea un token JWT con los datos proporcionados.
    
    Este token es lo que el frontend guarda después del login y envía
    en cada petición para probar que el usuario está autenticado.
    
    Args:
        data: Datos a incluir en el token (normalmente user_id, email, etc.)
        expires_delta: Tiempo personalizado de expiración (usa default si es None)
    
    Returns:
        str: Token JWT codificado listo para enviar al frontend
    
    Raises:
        ValueError: Si la codificación del token falla
    """
    to_encode = data.copy()
    
    # Calculamos cuándo expira el token
    expire = datetime.utcnow() + (
        expires_delta if expires_delta 
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(
            to_encode, 
            JWT_SECRET_KEY, 
            algorithm=JWT_ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        raise ValueError(f"Error codificando token JWT: {e}")

def register_admin_session(
    db: mysql.connector.connection.MySQLConnection, 
    admin_id: int, 
    token: str, 
    ip_address: Optional[str] = None, 
    navegador: Optional[str] = None
) -> Dict[str, Any]:
    """
    Registra una nueva sesión de administrador en la BD.
    
    Esto es útil para tracking de sesiones - puedes ver quién está
    logueado, desde dónde, y cuándo expiran los tokens. También permite
    invalidar sesiones específicas si es necesario.
    
    Args:
        db: Conexión a la base de datos
        admin_id: ID del administrador
        token: Token JWT que se generó
        ip_address: IP desde donde se conectó (opcional)
        navegador: Info del browser (opcional)
        
    Returns:
        Dict con los datos de la sesión creada
        
    Raises:
        DatabaseError: Si no se puede crear la sesión
    """
    # Calculamos cuándo expira basándome en la configuración del token
    expires = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    
    # Usamos el modelo para crear la sesión en BD
    session_id = SesionAdminModel.crear(
        admin_id=admin_id,
        token=token,
        fecha_expiracion=expires,
        ip_address=ip_address,
        navegador=navegador,
        activa=True
    )
    
    # Devolvemos la sesión recién creada
    session = SesionAdminModel.obtener_por_id(session_id)
    return session

async def get_current_admin(
    token: str = Depends(oauth2_scheme), 
    db: mysql.connector.connection.MySQLConnection = Depends(get_db)
) -> Dict[str, Any]:
    """
    Obtiene el administrador actual desde el token JWT.
    
    Esta función es la que FastAPI usa automáticamente cuando pones
    'current_admin: Depends(get_current_admin)' en un endpoint.
    
    Decodifica el token, verifica que sea válido, y devuelve los datos
    del admin. Si algo falla, lanza una excepción 401 Unauthorized.
    
    Args:
        token: Token JWT del header Authorization
        db: Conexión a la BD (se inyecta automáticamente)
    
    Returns:
        Dict con los datos del administrador actual
        
    Raises:
        HTTPException: Si el token es inválido, expirado, o el admin no existe
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodificamos el token JWT para extraer la información
        payload = jwt.decode(
            token, 
            JWT_SECRET_KEY, 
            algorithms=[JWT_ALGORITHM]
        )
        email: str = payload.get("sub")
        admin_id: int = payload.get("admin_id")
        
        # Validamos que el token tenga los datos requeridos
        if email is None or admin_id is None:
            raise credentials_exception
            
        token_data = schemas.TokenData(email=email, admin_id=admin_id)
        
    except JWTError:
        raise credentials_exception
    
    cursor = db.cursor(dictionary=True)
    
    try:
        # Verificamos que el administrador exista y esté activo
        cursor.execute(
            "SELECT * FROM administradores WHERE id = %s", 
            (token_data.admin_id,)
        )
        admin = cursor.fetchone()
        
        if admin is None or not admin["activo"]:
            raise credentials_exception
        
    # Verificamos que la sesión siga siendo válida
        cursor.execute("""
        SELECT * FROM sesiones_admin
        WHERE admin_id = %s AND token = %s AND activa = TRUE 
        AND fecha_expiracion > %s
        """, (admin["id"], token, datetime.utcnow()))
        
        session = cursor.fetchone()
        
        if not session:
            raise credentials_exception
        
        return admin
        
    except mysql.connector.Error as e:
        # Log de error de base de datos (en producción usar logger estructurado)
        print(f"Error de base de datos en get_current_admin: {e}")
        raise credentials_exception
    finally:
        cursor.close()