from huggingface_hub import InferenceClient
from backend.config import HF_API_KEY
import logging
import asyncio

logger = logging.getLogger(__name__)

class HuggingFaceService:
    _client = None

    @classmethod
    async def get_client_async(cls) -> InferenceClient:
        """Obtiene o inicializa el cliente de inferencia de Hugging Face de forma async."""
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
        """Obtiene o inicializa el cliente de inferencia de Hugging Face."""
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
    async def verify_connection_async(cls) -> bool:
        """Verifica si la conexión con Hugging Face es válida de forma async."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                client = await cls.get_client_async()
                logger.info("Conexión con Hugging Face verificada.")
                return True
            except (ValueError, ConnectionError) as e:
                logger.error(f"Intento {attempt + 1} - Fallo en la verificación de conexión con Hugging Face: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2.0 * (attempt + 1))  # Backoff exponencial
                else:
                    return False
            except Exception as e:
                logger.error(f"Error inesperado al verificar conexión con Hugging Face: {e}")
                return False

    @classmethod
    def verify_connection(cls) -> bool:
        """Verifica si la conexión con Hugging Face es válida."""
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
