from huggingface_hub import InferenceClient
import sys
import os

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import HF_API_KEY
from .resilience_service import ResilienceService
import logging
import asyncio

logger = logging.getLogger(__name__)

class HuggingFaceService:
    _client = None

    @classmethod
    @ResilienceService.simple_retry(attempts=3, delay=2.0)
    async def get_client_async(cls) -> InferenceClient:
        """Obtiene o inicializa (si no existe) el cliente de inferencia de Hugging Face (versión asíncrona)."""
        if cls._client is None:
            if not HF_API_KEY:
                logger.error("API key de Hugging Face no configurada correctamente.")
                raise ValueError("API key de Hugging Face no configurada")
                
            try:
                cls._client = InferenceClient(api_key=HF_API_KEY)
                logger.info("Cliente de Hugging Face inicializado con éxito.")
            except Exception as e:
                logger.error(f"Error al inicializar el cliente de Hugging Face: {e}")
                raise ConnectionError(f"No se pudo inicializar el cliente de HF: {e}")
        return cls._client

    @classmethod
    def get_client(cls) -> InferenceClient:
        """Obtiene o inicializa (si no existe) el cliente de inferencia de Hugging Face (modo síncrono)."""
        if cls._client is None:
            if not HF_API_KEY:
                logger.error("API key de Hugging Face no configurada correctamente.")
                raise ValueError("API key de Hugging Face no configurada")
                
            try:
                cls._client = InferenceClient(api_key=HF_API_KEY)
                logger.info("Cliente de Hugging Face inicializado con éxito.")
            except Exception as e:
                logger.error(f"Error al inicializar el cliente de Hugging Face: {e}")
                raise ConnectionError(f"No se pudo inicializar el cliente de HF: {e}")
        return cls._client

    @classmethod
    @ResilienceService.resilient_hf_call(
        timeout_seconds=30.0,
        retry_attempts=3,
        fallback_response=None
    )
    async def verify_connection_async(cls) -> bool:
        """Verifica (asíncrono) que podemos crear y usar el cliente de Hugging Face correctamente."""
        try:
            client = await cls.get_client_async()
            logger.info("Conexión con Hugging Face verificada.")
            return True
        except (ValueError, ConnectionError) as e:
            logger.error(f"Fallo en la verificación de conexión con Hugging Face: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al verificar conexión con Hugging Face: {e}")
            return False

    @classmethod
    def verify_connection(cls) -> bool:
        """Verifica (síncrono) que podemos crear y usar el cliente de Hugging Face correctamente."""
        try:
            client = cls.get_client()
            logger.info("Conexión con Hugging Face verificada.")
            return True
        except (ValueError, ConnectionError) as e:
            logger.error(f"Fallo en la verificación de conexión con Hugging Face: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al verificar conexión con Hugging Face: {e}")
            return False

# Exportar una instancia o métodos estáticos para uso fácil
hf_client = HuggingFaceService.get_client
hf_client_async = HuggingFaceService.get_client_async
verify_hf_connection = HuggingFaceService.verify_connection
verify_hf_connection_async = HuggingFaceService.verify_connection_async