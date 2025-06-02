import logging
import asyncio
from .huggingface_service import hf_client, hf_client_async
from .resilience_service import ResilienceService

logger = logging.getLogger(__name__)

@ResilienceService.resilient_hf_call(
    timeout_seconds=45.0,
    retry_attempts=3,
    fallback_response="Lo siento, el servicio no está disponible en este momento. Por favor, inténtalo más tarde."
)
async def get_llm_response_async(user_input: str) -> str:
    """Obtiene una respuesta del modelo LLM de forma async con resiliencia."""
    try:
        client = await hf_client_async()
        # Aquí iría la lógica específica para llamar al LLM
        # Ejemplo simple:
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: client.conversational(user_input)
        )
        # Asumiendo que la respuesta tiene un formato específico
        generated_text = response.get('generated_text', "Lo siento, no pude procesar tu solicitud.")
        logger.info(f"Respuesta LLM generada para: '{user_input[:30]}...'")
        return generated_text
    except Exception as e:
        logger.error(f"Error al obtener respuesta del LLM: {e}")
        raise  # Relanzar para que el sistema de resiliencia lo maneje

def get_llm_response(user_input: str) -> str:
    """Obtiene una respuesta del modelo LLM."""
    try:
        client = hf_client() # Obtener cliente de HF
        # Aquí iría la lógica específica para llamar al LLM
        # Ejemplo simple:
        response = client.conversational(user_input)
        # Asumiendo que la respuesta tiene un formato específico
        generated_text = response.get('generated_text', "Lo siento, no pude procesar tu solicitud.")
        logger.info(f"Respuesta LLM generada para: '{user_input[:30]}...'")
        return generated_text
    except Exception as e:
        logger.error(f"Error al obtener respuesta del LLM: {e}")
        return "Hubo un error al contactar al asistente."

# Ya no se necesita la función legacy
# def obtener_respuesta_legacy(user_input: str) -> str:
#     logger.warning("Usando función legacy 'obtener_respuesta'. Considerar migrar a 'get_llm_response'.")
#     return get_llm_response(user_input)

# La función `verificar_conexion` ahora está en `huggingface_service`
# from backend.services.huggingface_service import verify_hf_connection as verificar_conexion 