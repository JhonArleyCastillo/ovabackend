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
    """
    Schema for changing administrator password.
    
    Attributes:
        password_actual (str): Current password for verification.
        nueva_password (str): New password with minimum 8 characters.
    """
    password_actual: str = Field(..., description="Current password")
    nueva_password: str = Field(
        ..., 
        min_length=8,
        description="New password (8+ chars, letters, numbers, symbols)"
    )
    
    @validator('nueva_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Validate password strength requirements.
        
        Args:
            v (str): Password to validate.
            
        Returns:
            str: Validated password.
            
        Raises:
            ValueError: If password doesn't meet requirements.
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
    """
    Base model for administrator sessions.
    
    Attributes:
        admin_id (int): Administrator's unique identifier.
        token (str): Session token.
        ip_address (Optional[str]): Client IP address.
        navegador (Optional[str]): Browser information.
    """
    admin_id: int
    token: str
    ip_address: Optional[str] = None
    navegador: Optional[str] = None

class SesionAdminResponse(SesionAdminBase):
    """
    Administrator session data for API responses.
    
    Attributes:
        id (int): Session unique identifier.
        fecha_inicio (datetime): Session start time.
        fecha_expiracion (datetime): Session expiration time.
        activa (bool): Whether session is active.
        admin_email (str): Administrator's email.
        admin_nombre (str): Administrator's name.
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
    """
    Schema for creating a new contact message.
    
    Attributes:
        nombre_completo (str): Full name of the contact person.
        email (EmailStr): Valid email address.
        asunto (str): Message subject.
        mensaje (str): Message content.
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
        """
        Validate that the full name is not empty.
        
        Args:
            v (str): Full name to validate.
            
        Returns:
            str: Validated and trimmed full name.
            
        Raises:
            ValueError: If name is empty after stripping whitespace.
        """
        if not v.strip():
            raise ValueError('Full name cannot be empty')
        return v.strip()

    @validator('asunto')
    @classmethod
    def asunto_must_be_valid(cls, v: str) -> str:
        """
        Validate that the subject is not empty.
        
        Args:
            v (str): Subject to validate.
            
        Returns:
            str: Validated and trimmed subject.
            
        Raises:
            ValueError: If subject is empty after stripping whitespace.
        """
        if not v.strip():
            raise ValueError('Subject cannot be empty')
        return v.strip()

    @validator('mensaje')
    @classmethod
    def mensaje_must_be_valid(cls, v: str) -> str:
        """
        Validate that the message is not empty.
        
        Args:
            v (str): Message to validate.
            
        Returns:
            str: Validated and trimmed message.
            
        Raises:
            ValueError: If message is empty after stripping whitespace.
        """
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()

class ContactoResponse(ContactoCreate):
    """
    Contact message data for API responses.
    
    Attributes:
        id (int): Contact message unique identifier.
        fecha_envio (datetime): Message send timestamp.
        leido (bool): Whether message has been read.
        respondido (bool): Whether message has been responded to.
    """
    id: int
    fecha_envio: datetime
    leido: bool
    respondido: bool

    class Config:
        from_attributes = True
        allow_population_by_field_name = True

class ContactoUpdate(BaseModel):
    """
    Schema for updating contact message status.
    
    Attributes:
        leido (Optional[bool]): Mark message as read/unread.
        respondido (Optional[bool]): Mark message as responded/not responded.
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
    """
    Base user model with common fields.
    
    Attributes:
        email (EmailStr): Valid email address.
        nombre (str): User's display name.
    """
    email: EmailStr = Field(..., description="Valid email address")
    nombre: str = Field(..., description="User's display name")

class UsuarioCreate(UsuarioBase):
    """
    Schema for creating a new user/subscriber.
    
    Inherits all fields from UsuarioBase without additional requirements.
    """
    pass

class UsuarioResponse(UsuarioBase):
    """
    User data for API responses.
    
    Attributes:
        id (int): User's unique identifier.
        activo (bool): Whether user account is active.
        fecha_registro (datetime): User registration timestamp.
    """
    id: int
    activo: bool
    fecha_registro: datetime

    class Config:
        from_attributes = True