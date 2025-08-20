"""
Modelos mínimos para mensajes de WebSocket.

Incluye:
- MessageType (Enum)
- TextMessage
- ErrorMessage
- ConnectionMessage
- TypingMessage
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class MessageType(str, Enum):
	TEXT = "text"
	TYPING = "typing"
	ERROR = "error"
	CONNECTED = "connected"
	DISCONNECTED = "disconnected"


class TextMessage(BaseModel):
	type: MessageType = Field(default=MessageType.TEXT)
	id: Optional[str] = None
	text: str
	is_user: bool = False


class TypingMessage(BaseModel):
	type: MessageType = Field(default=MessageType.TYPING)
	is_typing: bool = True


class ErrorMessage(BaseModel):
	type: MessageType = Field(default=MessageType.ERROR)
	id: Optional[str] = None
	error: str
	code: Optional[int] = None
	details: Optional[Dict[str, Any]] = None


class ConnectionMessage(BaseModel):
	type: MessageType = Field(default=MessageType.CONNECTED)
	client_id: Optional[str] = None
	status: str = "connected"


__all__ = [
	"MessageType",
	"TextMessage",
	"TypingMessage",
	"ErrorMessage",
	"ConnectionMessage",
]

