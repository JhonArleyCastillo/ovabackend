"""
Definición de modelos de datos para la aplicación.

Este archivo contiene las estructuras de datos utilizadas para estandarizar
los mensajes entre el cliente y el servidor.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class MessageType(str, Enum):
    """Tipos de mensajes soportados en el sistema."""
    TEXT = "text"                   # Mensaje de texto simple
    AUDIO = "audio"                 # Mensaje con audio
    IMAGE = "image"                 # Mensaje con imagen
    SIGN_LANGUAGE = "sign_language" # Mensaje de lenguaje de señas
    TYPING = "typing"               # Indicador de "escribiendo..."
    ERROR = "error"                 # Mensaje de error
    CONNECTED = "connected"         # Notificación de conexión
    DISCONNECTED = "disconnected"   # Notificación de desconexión

class MessageStatus(str, Enum):
    """Estados posibles de un mensaje."""
    SENDING = "sending"     # Mensaje enviándose
    DELIVERED = "delivered" # Mensaje entregado
    READ = "read"           # Mensaje leído
    FAILED = "failed"       # Error al entregar

class BaseMessage(BaseModel):
    """Estructura base para todos los mensajes."""
    type: MessageType
    timestamp: str = Field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())
    id: Optional[str] = None
    
class TextMessage(BaseMessage):
    """Mensaje de texto simple."""
    type: MessageType = MessageType.TEXT
    text: str
    is_user: bool = False

class AudioMessage(BaseMessage):
    """Mensaje con contenido de audio."""
    type: MessageType = MessageType.AUDIO
    text: Optional[str] = None  # Transcripción opcional
    audio: str  # Audio en formato base64
    is_user: bool = False

class ImageMessage(BaseMessage):
    """Mensaje con imagen."""
    type: MessageType = MessageType.IMAGE
    text: Optional[str] = None  # Descripción opcional
    image: str  # Imagen en formato base64
    objects: Optional[List[Dict[str, Any]]] = None  # Objetos detectados
    is_user: bool = False

class SignLanguageMessage(BaseMessage):
    """Mensaje de análisis de lenguaje de señas."""
    type: MessageType = MessageType.SIGN_LANGUAGE
    text: str  # Interpretación
    image: str  # Imagen en formato base64
    confidence: float
    alternatives: Optional[List[Dict[str, Any]]] = None
    is_user: bool = False

class TypingMessage(BaseMessage):
    """Indicador de que el usuario está escribiendo."""
    type: MessageType = MessageType.TYPING
    is_typing: bool = True

class ErrorMessage(BaseMessage):
    """Mensaje de error."""
    type: MessageType = MessageType.ERROR
    error: str
    code: Optional[int] = None
    details: Optional[Dict[str, Any]] = None

class ConnectionMessage(BaseMessage):
    """Mensaje de estado de conexión."""
    type: MessageType = Field(default=MessageType.CONNECTED)
    client_id: Optional[str] = None
    status: str = "connected"