"""
Pydantic data schemas for API validation and documentation.

This module contains Pydantic models for validating and documenting data
that is sent and received through the API endpoints. All models include
proper type hints, validation rules, and documentation.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
import re

# ===== Authentication Schemas =====

class TokenData(BaseModel):
    """
    JWT token payload data structure.
    
    Attributes:
        email (str): Administrator's email address.
        admin_id (int): Administrator's unique identifier.
    """
    email: str
    admin_id: int

class Token(BaseModel):
    """
    JWT access token response structure.
    
    Attributes:
        access_token (str): JWT token string.
        token_type (str): Token type (typically "bearer").
        admin_id (int): Administrator's unique identifier.
        email (str): Administrator's email address.
        nombre (str): Administrator's display name.
        es_superadmin (bool): Whether user has superadmin privileges.
    """
    access_token: str
    token_type: str
    admin_id: int
    email: str
    nombre: str
    es_superadmin: bool

# ===== Administrator Schemas =====

class AdminBase(BaseModel):
    """
    Base administrator model with common fields.
    
    Attributes:
        email (EmailStr): Valid email address.
        nombre (str): Administrator's display name.
    """
    email: EmailStr
    nombre: str

class AdminCreate(AdminBase):
    """
    Schema for creating a new administrator account.
    
    Attributes:
        password (str): Password with minimum 6 characters.
        es_superadmin (bool): Whether to grant superadmin privileges.
    """
    password: str = Field(..., min_length=6, description="Minimum 6 characters")
    es_superadmin: bool = Field(default=False, description="Grant superadmin access")

class AdminUpdate(BaseModel):
    """
    Schema for updating administrator information.
    
    All fields are optional for partial updates.
    
    Attributes:
        nombre (Optional[str]): New display name.
        email (Optional[EmailStr]): New email address.
        es_superadmin (Optional[bool]): Change superadmin status.
        activo (Optional[bool]): Enable/disable account.
    """
    nombre: Optional[str] = Field(None, description="Administrator display name")
    email: Optional[EmailStr] = Field(None, description="Valid email address")
    es_superadmin: Optional[bool] = Field(None, description="Superadmin privileges")
    activo: Optional[bool] = Field(None, description="Account active status")

class AdminResponse(AdminBase):
    """
    Administrator data for API responses.
    
    Attributes:
        id (int): Administrator's unique identifier.
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