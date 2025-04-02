import logging
from services.huggingface_service import hf_client

logger = logging.getLogger(__name__)

def speech_to_text(audio_bytes: bytes) -> str:
    """Convierte audio a texto usando un modelo STT."""
    try:
        client = hf_client()
        # Lógica para llamar al modelo STT
        # Ejemplo:
        result = client.automatic_speech_recognition(audio_bytes)
        text = result.get('text', "")
        logger.info(f"Audio convertido a texto: '{text[:50]}...'")
        return text
    except Exception as e:
        logger.error(f"Error en STT: {e}")
        return "Error al transcribir el audio."

def text_to_speech(text: str) -> bytes | None:
    """Genera audio a partir de texto usando un modelo TTS."""
    try:
        client = hf_client()
        # Lógica para llamar al modelo TTS
        # Ejemplo:
        audio_response = client.text_to_speech(text)
        # Asumiendo que devuelve los bytes del audio directamente
        logger.info(f"Audio generado para texto: '{text[:50]}...'")
        return audio_response
    except Exception as e:
        logger.error(f"Error en TTS: {e}")
        return None

# Funciones legacy eliminadas
# def convertir_audio_a_texto(audio_bytes: bytes) -> str:
#     logger.warning("Usando función legacy 'convertir_audio_a_texto'. Considerar migrar a 'speech_to_text'.")
#     return speech_to_text(audio_bytes)
# 
# def generar_voz(text: str) -> bytes | None:
#     logger.warning("Usando función legacy 'generar_voz'. Considerar migrar a 'text_to_speech'.")
#     return text_to_speech(text) 