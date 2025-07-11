"""
Utilidades de servicio consolidadas para eliminar redundancia en patrones de servicio.
"""
import asyncio
import logging
from typing import Any, Callable, Dict, Optional, Union
from functools import wraps
import time
import sys
import os

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.resilience_service import ResilienceService
from fastapi import HTTPException, UploadFile, Request
import io
from PIL import Image
from utils import validate_image_magic_bytes

logger = logging.getLogger(__name__)


class ServiceBase:
    """Clase base para todos los servicios con patrones comunes."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(f"{__name__}.{service_name}")
    
    def log_operation(self, operation: str, details: str = ""):
        """Registrar operaciones de servicio de manera consistente."""
        self.logger.info(f"{self.service_name} - {operation}: {details}")
    
    def log_error(self, operation: str, error: Exception):
        """Registrar errores de servicio de manera consistente."""
        self.logger.error(f"{self.service_name} - Error in {operation}: {error}")


class AsyncServiceMixin:
    """Mixin para patrones comunes de servicios asincrónicos."""
    
    @staticmethod
    def with_timeout(timeout_seconds: float = 30.0):
        """Decorador para agregar límite de tiempo a operaciones asyncio."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Timeout en {func.__name__} después de {timeout_seconds}s")
                    raise Exception(f"Operación {func.__name__} excedió el tiempo límite")
            return wrapper
        return decorator
    
    @staticmethod
    def with_retry(max_attempts: int = 3, delay: float = 1.0):
        """Decorador para agregar lógica de reintentos a operaciones asincrónicas."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            logger.warning(f"Intento {attempt + 1} fallido en {func.__name__}: {e}")
                            await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                        else:
                            logger.error(f"Todos los intentos fallaron en {func.__name__}: {e}")
                
                raise last_exception
            return wrapper
        return decorator


class HuggingFaceServiceMixin:
    """Patrones comunes para servicios de Hugging Face."""
    
    @staticmethod
    def with_resilience(
        timeout_seconds: float = 60.0,
        retry_attempts: int = 3,
        fallback_response: Any = None
    ):
        """Aplicar patrones de resiliencia usando ResilienceService."""
        return ResilienceService.resilient_hf_call(
            timeout_seconds=timeout_seconds,
            retry_attempts=retry_attempts,
            fallback_response=fallback_response
        )
    
    @staticmethod
    def validate_hf_response(response: Any) -> bool:
        """Validar respuestas de la API de Hugging Face."""
        if not response:
            return False
        
        # Agregar lógica de validación específica basada en el formato de respuesta esperado
        if isinstance(response, dict):
            return len(response) > 0
        elif isinstance(response, list):
            return len(response) > 0
        
        return True
    
    @staticmethod
    def format_hf_error(error: Exception) -> str:
        """Formatear errores de Hugging Face consistentemente."""
        error_msg = str(error)
        
        # Common HF error patterns
        if "rate limit" in error_msg.lower():
            return "Límite de tasa excedido en HuggingFace. Intente más tarde."
        elif "timeout" in error_msg.lower():
            return "Tiempo de espera agotado en HuggingFace."
        elif "unauthorized" in error_msg.lower():
            return "Error de autorización en HuggingFace."
        else:
            return f"Error en HuggingFace: {error_msg}"


class ImageServiceMixin:
    """Patrones comunes para servicios de procesamiento de imágenes."""
    
    @staticmethod
    def validate_image_format(image_data: Any) -> bool:
        """Validar formato de imagen."""
        # Agregar lógica de validación de formato de imagen
        return True
    
    @staticmethod
    def resize_image_if_needed(image: Any, max_size: tuple = (1024, 1024)) -> Any:
        """Redimensionar imagen si excede dimensiones máximas."""
        # Agregar lógica de redimensionamiento de imagen si es necesario
        return image
    
    @staticmethod
    def get_image_metadata(image: Any) -> Dict[str, Any]:
        """Extraer metadatos de la imagen."""
        return {
            "format": "unknown",
            "size": (0, 0),
            "mode": "unknown"
        }


class AudioServiceMixin:
    """Patrones comunes para servicios de procesamiento de audio."""
    
    @staticmethod
    def validate_audio_format(audio_data: Any) -> bool:
        """Validar formato de audio."""
        return True
    
    @staticmethod
    def normalize_audio_level(audio_data: Any) -> Any:
        """Normalizar niveles de audio."""
        return audio_data
    
    @staticmethod
    def get_audio_duration(audio_data: Any) -> float:
        """Obtener duración de audio en segundos."""
        return 0.0


# Decoradores de servicio preconfigurados para casos de uso comunes
image_service_resilient = HuggingFaceServiceMixin.with_resilience(
    timeout_seconds=60.0,
    retry_attempts=3,
    fallback_response={"objects": [], "description": "Servicio no disponible"}
)

chat_service_resilient = HuggingFaceServiceMixin.with_resilience(
    timeout_seconds=45.0,
    retry_attempts=3,
    fallback_response="Lo siento, el servicio no está disponible en este momento."
)

audio_service_resilient = HuggingFaceServiceMixin.with_resilience(
    timeout_seconds=30.0,
    retry_attempts=2,
    fallback_response=b""  # Respuesta de audio vacía
)


# Helper asíncrono para cargar y validar imágenes en routers

async def load_and_validate_image(file: UploadFile, allowed_types: list[str]):
    """
    Lee y valida un archivo de imagen UploadFile.
    - Comprueba content_type
    - Valida magic bytes
    - Retorna objeto PIL.Image
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
    # Leer datos binarios
    image_data = await file.read()
    # Validar magic bytes
    is_valid, detected_type = validate_image_magic_bytes(image_data)
    if not is_valid or detected_type not in allowed_types:
        raise HTTPException(status_code=400, detail="La extensión de la imagen no es permitida")
    # Abrir con PIL
    try:
        return Image.open(io.BytesIO(image_data))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al abrir la imagen: {e}")


def extract_client_info(request: Request) -> dict:
    """
    Extrae información del cliente de una petición: dirección IP y user-agent.
    """
    ip_address = request.client.host if request else None
    user_agent = request.headers.get("user-agent") if request else None
    return {"ip_address": ip_address, "user_agent": user_agent}
