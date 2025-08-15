"""
Esquemas Pydantic para validación y documentación de la API.

Este módulo contiene los modelos Pydantic que validan y documentan
todos los datos que van y vienen a través de los endpoints de la API.

Como desarrollador fullstack, estos esquemas son súper importantes porque:
- Validan automáticamente los datos que llegan (ej: que el email sea válido)
- Generan la documentación automática en /docs
- Definen exactamente qué campos espera cada endpoint

Si FastAPI te dice que falta un campo o formato incorrecto, revisa estos esquemas.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
import re

# ===== Esquemas de Autenticación =====

class TokenData(BaseModel):
    """
    Estructura de datos del payload del token JWT.
    
    Esto es lo que va "dentro" del token cuando lo decodificas.
    """
    email: str        # Email del administrador
    admin_id: int     # ID único del admin

class Token(BaseModel):
    """
    Respuesta cuando el login es exitoso.
    
    Esto es lo que devuelve el endpoint /api/auth/token cuando
    el usuario hace login correctamente.
    """
    access_token: str    # El token JWT que el frontend guarda
    token_type: str      # Siempre "bearer" 
    admin_id: int        # ID del admin que se logueó
    email: str           # Email del admin
    nombre: str          # Nombre para mostrar en el UI
    es_superadmin: bool  # Si tiene privilegios de super admin

# ===== Esquemas de Administradores =====

class AdminBase(BaseModel):
    """
    Campos básicos que todos los administradores tienen.
    
    Otros esquemas heredan de este para no repetir código.
    """
    email: EmailStr  # Email válido (Pydantic valida automáticamente)
    nombre: str      # Nombre para mostrar

class AdminCreate(AdminBase):
    """
    Datos necesarios para crear un nuevo administrador.
    
    Usado en el endpoint de registro de admins.
    """
    password: str = Field(..., min_length=6, description="Mínimo 6 caracteres")
    es_superadmin: bool = Field(default=False, description="Dar acceso de super admin")

class AdminUpdate(BaseModel):
    """
    Esquema para actualizar información de administradores.
    
    Todos los campos son opcionales para permitir actualizaciones parciales.
    """
    nombre: Optional[str] = Field(None, description="Nuevo nombre para mostrar")
    email: Optional[EmailStr] = Field(None, description="Nuevo email válido")
    es_superadmin: Optional[bool] = Field(None, description="Cambiar privilegios de super admin")
    activo: Optional[bool] = Field(None, description="Activar/desactivar cuenta")

class AdminResponse(AdminBase):
    """
    Datos del administrador para respuestas de la API.
    
    Esto es lo que devuelve la API cuando consultas información de admins.
    Nunca incluye la contraseña por seguridad.
    """
    id: int
    es_superadmin: bool
    activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    class Config:
        from_attributes = True

class AdminChangePassword(BaseModel):
    """Esquema para cambiar la contraseña de un administrador.

    Atributos:
        password_actual (str): Contraseña actual para validar identidad.
        nueva_password (str): Nueva contraseña (mínimo 8 caracteres) que debe incluir letras, números y símbolos.
    """
    password_actual: str = Field(..., description="Contraseña actual")
    nueva_password: str = Field(
        ..., 
        min_length=8,
        description="Nueva contraseña (8+ caracteres, letras, números y símbolos)"
    )
    
    @validator('nueva_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Valida que la contraseña cumpla los requisitos mínimos de seguridad.

        Parámetros:
            v (str): Contraseña a validar.

        Retorna:
            str: La contraseña validada (sin modificar).

        Lanza:
            ValueError: Si no cumple longitud o composición exigida.
        """
        pattern = (
            r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[$@$!%*?&])'
            r'([A-Za-z\d$@$!%*?&][^ ]){8,}$'
        )
        description = (
            "Password must be at least 8 characters long and contain "
            "letters, numbers, and special symbols."
        )
        if not re.match(pattern, v):    
            raise ValueError(description)
        return v

# ===== Administrator Session Schemas =====

class SesionAdminBase(BaseModel):
    """Modelo base para sesiones de administradores.

    Atributos:
        admin_id (int): ID único del administrador.
        token (str): Token asociado a la sesión.
        ip_address (Optional[str]): Dirección IP del cliente.
        navegador (Optional[str]): Información del navegador.
    """
    admin_id: int
    token: str
    ip_address: Optional[str] = None
    navegador: Optional[str] = None

class SesionAdminResponse(SesionAdminBase):
    """Datos de una sesión de administrador para respuestas de la API.

    Atributos:
        id (int): ID único de la sesión.
        fecha_inicio (datetime): Cuándo se inició.
        fecha_expiracion (datetime): Cuándo expira.
        activa (bool): Si la sesión sigue activa.
        admin_email (str): Email del administrador.
        admin_nombre (str): Nombre del administrador.
    """
    id: int
    fecha_inicio: datetime
    fecha_expiracion: datetime
    activa: bool
    admin_email: str
    admin_nombre: str

    class Config:
        from_attributes = True

# ===== Contact Schemas =====

class ContactoCreate(BaseModel):
    """Esquema para crear un nuevo mensaje de contacto.

    Atributos:
        nombre_completo (str): Nombre completo de la persona que escribe.
        email (EmailStr): Correo válido.
        asunto (str): Asunto del mensaje.
        mensaje (str): Contenido del mensaje.
    """
    nombre_completo: str = Field(
        ..., 
        min_length=2, 
        max_length=200, 
        alias='nombre',
        description="Full name (2-200 characters)"
    )
    email: EmailStr = Field(..., description="Valid email address")
    asunto: str = Field(
        ..., 
        min_length=3, 
        max_length=200,
        description="Message subject (3-200 characters)"
    )
    mensaje: str = Field(
        ..., 
        min_length=10,
        description="Message content (minimum 10 characters)"
    )

    @validator('nombre_completo')
    @classmethod
    def nombre_must_be_valid(cls, v: str) -> str:
        """Valida que el nombre no esté vacío.

        Parámetros:
            v (str): Nombre completo a validar.

        Retorna:
            str: Nombre limpio (sin espacios extremos).

        Lanza:
            ValueError: Si el nombre queda vacío tras hacer strip().
        """
        if not v.strip():
            raise ValueError('Full name cannot be empty')
        return v.strip()

    @validator('asunto')
    @classmethod
    def asunto_must_be_valid(cls, v: str) -> str:
        """Valida que el asunto no esté vacío.

        Parámetros:
            v (str): Asunto a validar.

        Retorna:
            str: Asunto limpio.

        Lanza:
            ValueError: Si queda vacío tras strip().
        """
        if not v.strip():
            raise ValueError('Subject cannot be empty')
        return v.strip()

    @validator('mensaje')
    @classmethod
    def mensaje_must_be_valid(cls, v: str) -> str:
        """Valida que el mensaje no esté vacío.

        Parámetros:
            v (str): Mensaje a validar.

        Retorna:
            str: Mensaje limpio.

        Lanza:
            ValueError: Si queda vacío tras strip().
        """
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()

class ContactoResponse(ContactoCreate):
    """Datos de un mensaje de contacto para respuestas de API.

    Atributos:
        id (int): ID único del mensaje.
        fecha_envio (datetime): Cuándo se envió.
        leido (bool): Si fue marcado como leído.
        respondido (bool): Si se respondió.
    """
    id: int
    fecha_envio: datetime
    leido: bool
    respondido: bool

    class Config:
        from_attributes = True
        allow_population_by_field_name = True

class ContactoUpdate(BaseModel):
    """Esquema para actualizar el estado de un mensaje de contacto.

    Atributos:
        leido (Optional[bool]): Marcar como leído/no leído.
        respondido (Optional[bool]): Marcar como respondido/no respondido.
    """
    leido: Optional[bool] = Field(
        None, 
        description="Mark message as read"
    )
    respondido: Optional[bool] = Field(
        None, 
        description="Mark message as responded"
    )

# ===== User Schemas =====

class UsuarioBase(BaseModel):
    """Modelo base de usuario con campos comunes.

    Atributos:
        email (EmailStr): Correo válido.
        nombre (str): Nombre para mostrar.
    """
    email: EmailStr = Field(..., description="Valid email address")
    nombre: str = Field(..., description="User's display name")

class UsuarioCreate(UsuarioBase):
    """Esquema para crear un nuevo usuario/suscriptor.

    Hereda todos los campos de UsuarioBase sin requisitos extra.
    """
    pass

class UsuarioResponse(UsuarioBase):
    """Datos de usuario para respuestas de la API.

    Atributos:
        id (int): ID único del usuario.
        activo (bool): Si la cuenta está activa.
        fecha_registro (datetime): Fecha/hora de registro.
    """
    id: int
    activo: bool
    fecha_registro: datetime

    class Config:
        from_attributes = True