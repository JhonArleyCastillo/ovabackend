"""
Utilidades de servicio consolidadas para eliminar redundancia en patrones de servicio.
"""
import asyncio
import logging
from typing import Any, Callable, Dict, Optional, Union
from functools import wraps
import time

from backend.services.resilience_service import ResilienceService

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
