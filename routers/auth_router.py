"""
Rutas API para la autenticación y gestión de administradores.

Este archivo define los endpoints para el inicio de sesión de administradores,
la gestión de sus cuentas y el seguimiento de sesiones.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
import mysql.connector
import sys
import os

# Añadir el directorio raíz del proyecto al path de Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Ahora importamos desde backend con rutas absolutas
from backend.database import get_db
import backend.db_models as db_models
import backend.schemas as schemas
import backend.auth as auth

router = APIRouter(
    prefix="/api/auth",
    tags=["autenticación"],
    responses={404: {"description": "Recurso no encontrado"}}
)

@router.post("/token", response_model=schemas.Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: mysql.connector.connection.MySQLConnection = Depends(get_db),
    request: Request = None
):
    """
    Autentica un administrador y genera un token JWT.
    """
    admin = auth.authenticate_admin(db, form_data.username, form_data.password)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = {
        "sub": admin["email"],
        "admin_id": admin["id"]
    }
    
    access_token = auth.create_access_token(token_data)
    
    # Obtener información del cliente para la sesión
    ip_address = request.client.host if request else None
    user_agent = request.headers.get("user-agent") if request else None
    
    # Registrar la sesión
    auth.register_admin_session(
        db=db, 
        admin_id=admin["id"], 
        token=access_token,
        ip_address=ip_address,
        navegador=user_agent
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/admins/", response_model=schemas.AdminResponse)
async def crear_admin(
    admin: schemas.AdminCreate, 
    db: mysql.connector.connection.MySQLConnection = Depends(get_db),
    current_admin: dict = Depends(auth.get_current_admin)
):
    """
    Crea un nuevo administrador.
    Solo puede ser usado por administradores existentes.
    """
    # Verificar que el administrador actual sea un superadmin
    if not current_admin["es_superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para crear administradores"
        )
        
    # Verificar si el correo ya existe
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM administradores WHERE email = %s",
        (admin.email,)
    )
    db_admin = cursor.fetchone()
    
    if db_admin:
        cursor.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado"
        )
        
    # Crear el nuevo administrador
    hashed_password = auth.get_password_hash(admin.password)
    cursor.execute("""
    INSERT INTO administradores (email, nombre, hashed_password, es_superadmin, activo)
    VALUES (%s, %s, %s, %s, %s)
    """, (admin.email, admin.nombre, hashed_password, False, True))
    
    db.commit()
    new_admin_id = cursor.lastrowid
    
    # Obtener el administrador creado
    cursor.execute("SELECT * FROM administradores WHERE id = %s", (new_admin_id,))
    new_admin = cursor.fetchone()
    cursor.close()
    
    return new_admin

@router.get("/admins/", response_model=List[schemas.AdminResponse])
async def listar_admins(
    skip: int = 0,
    limit: int = 100,
    db: mysql.connector.connection.MySQLConnection = Depends(get_db),
    current_admin: dict = Depends(auth.get_current_admin)
):
    """
    Lista todos los administradores.
    Solo puede ser usado por superadmins.
    """
    if not current_admin["es_superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para ver la lista de administradores"
        )
    
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM administradores LIMIT %s OFFSET %s", (limit, skip))
    admins = cursor.fetchall()
    cursor.close()
        
    return admins

@router.get("/sessions/", response_model=List[schemas.SesionAdminResponse])
async def listar_sesiones(
    db: mysql.connector.connection.MySQLConnection = Depends(get_db),
    current_admin: dict = Depends(auth.get_current_admin)
):
    """
    Lista las sesiones activas del administrador actual.
    """
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
    SELECT * FROM sesiones_admin 
    WHERE admin_id = %s AND activa = TRUE
    """, (current_admin["id"],))
    
    sesiones = cursor.fetchall()
    cursor.close()
    
    return sesiones

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def cerrar_sesion(
    token: str = Depends(auth.oauth2_scheme),
    db: mysql.connector.connection.MySQLConnection = Depends(get_db),
    current_admin: dict = Depends(auth.get_current_admin)
):
    """
    Cierra la sesión actual del administrador.
    """
    cursor = db.cursor()
    cursor.execute("""
    UPDATE sesiones_admin SET activa = FALSE
    WHERE admin_id = %s AND token = %s AND activa = TRUE
    """, (current_admin["id"], token))
    
    db.commit()
    cursor.close()
    
    return None