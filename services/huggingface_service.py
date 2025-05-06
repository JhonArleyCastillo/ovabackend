from huggingface_hub import InferenceClient
# Importar el módulo dotenv para asegurar que las variables de entorno están cargadas
from dotenv import loaded as dotenv_loaded
# Cambiado a importación absoluta desde backend
from config import HF_API_KEY
import logging
import os

logger = logging.getLogger(__name__)

class HuggingFaceService:
    _client = None

    @classmethod
    def get_client(cls) -> InferenceClient:
        """Obtiene o inicializa el cliente de inferencia de Hugging Face."""
        if cls._client is None:
            if not HF_API_KEY:
                # Si la clave no está en config, intentar obtenerla directamente del entorno
                api_key = os.getenv("HF_API_KEY")
                if not api_key:
                    logger.error("API key de Hugging Face no configurada correctamente.")
                    raise ValueError("API key de Hugging Face no configurada")
                else:
                    # Usar la clave del entorno
                    key = api_key
            else:
                # Usar la clave de la configuración
                key = HF_API_KEY
                
            try:
                cls._client = InferenceClient(api_key=key)
                logger.info("Cliente de Hugging Face inicializado con éxito.")
            except Exception as e:
                logger.error(f"Error al inicializar el cliente de Hugging Face: {e}")
                raise ConnectionError(f"No se pudo inicializar el cliente de HF: {e}")
        return cls._client

    @classmethod
    def verify_connection(cls) -> bool:
        """Verifica si la conexión con Hugging Face es válida."""
        try:
            client = cls.get_client()
            # Realizar una operación simple para verificar la conexión, p.ej., listar modelos
            # Esto puede variar dependiendo de las capacidades del cliente/API
            # Aquí asumimos que obtener el cliente ya implica una verificación básica
            # o que una operación simple como listar tareas es suficiente.
            # client.list_inference_tasks() # Ejemplo si existiera tal método
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
verify_hf_connection = HuggingFaceService.verify_connection