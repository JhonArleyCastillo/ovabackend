"""
Modelos de datos para la comunicación frontend-backend.

Estos modelos definen la estructura de los mensajes que van y vienen
entre el frontend React y el backend FastAPI. Son como "contratos"
que aseguran que ambos lados entiendan el formato de los datos.

Como desarrollador fullstack, si cambias algo aquí, probablemente 
también necesites actualizar el frontend para que use la nueva estructura.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class MessageType(str, Enum):
    """Tipos de mensajes que el sistema puede manejar."""
    TEXT = "text"                   # Mensaje de texto normal
    # AUDIO = "audio"               # Removido para optimización en EC2
    IMAGE = "image"                 # Mensaje con imagen (detección general)
    SIGN_LANGUAGE = "sign_language" # Mensaje de reconocimiento ASL
    TYPING = "typing"               # Indicador de "escribiendo..."
    ERROR = "error"                 # Mensaje de error
    CONNECTED = "connected"         # Notificación de conexión establecida
    DISCONNECTED = "disconnected"   # Notificación de desconexión

class MessageStatus(str, Enum):
    """Estados que puede tener un mensaje durante su ciclo de vida."""
    SENDING = "sending"     # Se está enviando
    DELIVERED = "delivered" # Llegó al servidor
    READ = "read"           # El destinatario lo leyó
    FAILED = "failed"       # Falló el envío

class BaseMessage(BaseModel):
    """
    Modelo base para todos los mensajes.
    
    Todos los demás tipos de mensaje heredan de este.
    Incluye campos comunes como tipo, timestamp e ID.
    """
    type: MessageType
    timestamp: str = Field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())
    id: Optional[str] = None
    
class TextMessage(BaseMessage):
    """
    Mensaje de texto simple.
    
    Es el tipo más básico - solo texto que va del usuario al bot o viceversa.
    """
    type: MessageType = MessageType.TEXT
    text: str
    is_user: bool = False  # False = mensaje del bot, True = mensaje del usuario

# AudioMessage removido para optimización en EC2

class ImageMessage(BaseMessage):
    """
    Mensaje con imagen para detección general de objetos.
    
    Usado para fotos normales donde queremos detectar gatos, carros, etc.
    Para ASL usar SignLanguageMessage en su lugar.
    """
    type: MessageType = MessageType.IMAGE
    text: Optional[str] = None  # Descripción de la imagen (opcional)
    image: str  # Imagen codificada en base64
    objects: Optional[List[Dict[str, Any]]] = None  # Objetos detectados
    is_user: bool = False

class SignLanguageMessage(BaseMessage):
    """
    Mensaje específico para reconocimiento de lenguaje de señas ASL.
    
    Este es el modelo que se usa cuando el frontend envía una imagen ASL
    y el backend devuelve qué signo reconoció.
    """
    type: MessageType = MessageType.SIGN_LANGUAGE
    text: str  # Qué signo se reconoció (ej: "A", "B", "Hola")
    image: str  # Imagen original en base64
    confidence: float  # Confianza del reconocimiento (0-100)
    alternatives: Optional[List[Dict[str, Any]]] = None  # Otras posibilidades
    is_user: bool = False

class TypingMessage(BaseMessage):
    """
    Indicador de que alguien está escribiendo.
    
    Se usa para mostrar esos puntitos de "escribiendo..." en el chat.
    """
    type: MessageType = MessageType.TYPING
    is_typing: bool = True

class ErrorMessage(BaseMessage):
    """
    Mensaje cuando algo sale mal.
    
    Se envía al frontend cuando hay errores para que pueda mostrar
    mensajes apropiados al usuario.
    """
    type: MessageType = MessageType.ERROR
    error: str  # Descripción del error
    code: Optional[int] = None  # Código de error (opcional)
    details: Optional[Dict[str, Any]] = None  # Detalles adicionales

class ConnectionMessage(BaseMessage):
    """
    Mensaje de estado de conexión WebSocket.
    
    Se envía cuando alguien se conecta o desconecta del chat.
    """
    type: MessageType = Field(default=MessageType.CONNECTED)
    client_id: Optional[str] = None  # ID del cliente que se conectó/desconectó
    status: str = "connected"  # "connected" o "disconnected"