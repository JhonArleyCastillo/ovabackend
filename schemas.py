"""
Esquemas de datos para la API.

Este archivo contiene los modelos Pydantic para validar y documentar los datos
que se envían y reciben a través de la API.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator

# Esquemas de autenticación

class TokenData(BaseModel):
    """Datos contenidos en un token JWT."""
    email: str
    admin_id: int

class Token(BaseModel):
    """Token de acceso JWT."""
    access_token: str
    token_type: str
    admin_id: int
    email: str
    nombre: str
    es_superadmin: bool

# Esquemas de administradores

class AdminBase(BaseModel):
    """Modelo base para administradores."""
    email: EmailStr
    nombre: str

class AdminCreate(AdminBase):
    """Datos para crear un nuevo administrador."""
    password: str = Field(..., min_length=6)
    es_superadmin: bool = False

class AdminUpdate(BaseModel):
    """Datos para actualizar un administrador."""
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    es_superadmin: Optional[bool] = None
    activo: Optional[bool] = None

class AdminResponse(AdminBase):
    """Respuesta con datos de administrador."""
    id: int
    es_superadmin: bool
    activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    class Config:
        from_attributes = True

class AdminChangePassword(BaseModel):
    """Datos para cambiar la contraseña de un administrador."""
    password_actual: str
    nueva_password: str = Field(..., min_length=6)

# Esquemas de sesiones de administradores

class SesionAdminBase(BaseModel):
    """Modelo base para sesiones de administradores."""
    admin_id: int
    token: str
    ip_address: Optional[str] = None
    navegador: Optional[str] = None

class SesionAdminResponse(SesionAdminBase):
    """Respuesta con datos de sesión de administrador."""
    id: int
    fecha_inicio: datetime
    fecha_expiracion: datetime
    activa: bool
    admin_email: str
    admin_nombre: str

    class Config:
        from_attributes = True

# Esquemas de contacto

class ContactoCreate(BaseModel):
    """Datos para crear un nuevo mensaje de contacto."""
    nombre: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    asunto: str = Field(..., min_length=3, max_length=200)
    mensaje: str = Field(..., min_length=10)

    @validator('nombre')
    def nombre_must_be_valid(cls, v):
        if not v.strip():
            raise ValueError('El nombre no puede estar vacío')
        return v.strip()

    @validator('asunto')
    def asunto_must_be_valid(cls, v):
        if not v.strip():
            raise ValueError('El asunto no puede estar vacío')
        return v.strip()

    @validator('mensaje')
    def mensaje_must_be_valid(cls, v):
        if not v.strip():
            raise ValueError('El mensaje no puede estar vacío')
        return v.strip()

class ContactoResponse(ContactoCreate):
    """Respuesta con datos de mensaje de contacto."""
    id: int
    fecha_envio: datetime
    leido: bool
    respondido: bool

    class Config:
        from_attributes = True

class ContactoUpdate(BaseModel):
    """Datos para actualizar un mensaje de contacto."""
    leido: Optional[bool] = None
    respondido: Optional[bool] = None

# Esquemas de usuarios

class UsuarioBase(BaseModel):
    """Modelo base para usuarios."""
    email: EmailStr
    nombre: str

class UsuarioCreate(UsuarioBase):
    """Datos para crear un nuevo usuario/suscriptor."""
    pass

class UsuarioResponse(UsuarioBase):
    """Respuesta con datos de usuario."""
    id: int
    activo: bool
    fecha_registro: datetime

    class Config:
        from_attributes = True