"""
Rutas API para la gestión de usuarios/suscriptores.

Este archivo define los endpoints para registrar usuarios mediante su correo electrónico
y gestionar la lista de suscriptores.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
import mysql.connector

# Changed from relative to absolute imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.database import get_db
import db_models, schemas, auth

router = APIRouter(
    prefix="/api/usuarios",
    tags=["usuarios"],
    responses={404: {"description": "Recurso no encontrado"}}
)

@router.post("/", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def registrar_usuario(usuario: schemas.UsuarioCreate, db: mysql.connector.connection.MySQLConnection = Depends(get_db)):
    """
    Registra un nuevo usuario con su correo electrónico.
    """
    # Verificar si el usuario ya existe
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM usuarios WHERE email = %s", 
        (usuario.email,)
    )
    db_usuario = cursor.fetchone()
    
    if db_usuario:
        # Si el usuario ya existe pero estaba inactivo, lo reactivamos
        if not db_usuario["activo"]:
            cursor.execute(
                "UPDATE usuarios SET activo = 1 WHERE id = %s",
                (db_usuario["id"],)
            )
            db.commit()
            
            cursor.execute(
                "SELECT * FROM usuarios WHERE id = %s",
                (db_usuario["id"],)
            )
            db_usuario = cursor.fetchone()
            cursor.close()
            return db_usuario
        
        # Si ya está activo, informamos que ya está registrado
        cursor.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado"
        )
    
    # Crear un nuevo usuario
    activo_int = 1  # Por defecto activo
    cursor.execute(
        "INSERT INTO usuarios (email, nombre, activo) VALUES (%s, %s, %s)",
        (usuario.email, usuario.nombre, activo_int)
    )
    db.commit()
    
    new_id = cursor.lastrowid
    cursor.execute(
        "SELECT * FROM usuarios WHERE id = %s",
        (new_id,)
    )
    nuevo_usuario = cursor.fetchone()
    cursor.close()
    return nuevo_usuario

@router.get("/", response_model=List[schemas.UsuarioResponse])
def obtener_usuarios(
    skip: int = 0, 
    limit: int = 100, 
    db: mysql.connector.connection.MySQLConnection = Depends(get_db),
    current_admin: dict = Depends(auth.get_current_admin)
):
    """
    Obtiene la lista de usuarios registrados.
    Requiere autenticación como administrador.
    """
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM usuarios ORDER BY id DESC LIMIT %s OFFSET %s", 
        (limit, skip)
    )
    usuarios = cursor.fetchall()
    cursor.close()
    return usuarios

@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_usuario(
    usuario_id: int, 
    db: mysql.connector.connection.MySQLConnection = Depends(get_db),
    current_admin: dict = Depends(auth.get_current_admin)
):
    """
    Desactiva un usuario por su ID.
    Requiere autenticación como administrador.
    """
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM usuarios WHERE id = %s",
        (usuario_id,)
    )
    usuario = cursor.fetchone()
    
    if not usuario:
        cursor.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    cursor.execute(
        "UPDATE usuarios SET activo = 0 WHERE id = %s",
        (usuario_id,)
    )
    db.commit()
    cursor.close()
    return None