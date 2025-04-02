import base64
import numpy as np
import cv2
import logging

logger = logging.getLogger(__name__)

def decode_base64_image(base64_string: str) -> np.ndarray | None:
    """Decodifica una imagen en formato base64 a un array numpy."""
    try:
        # Eliminar prefijo si existe
        if "base64," in base64_string:
            base64_string = base64_string.split("base64,")[1]
            
        image_bytes = base64.b64decode(base64_string)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            logger.error("La imagen no pudo ser decodificada por OpenCV")
            return None
        return img
    except Exception as e:
        logger.error(f"Error al decodificar imagen base64: {e}")
        return None

def encode_audio_to_base64(audio_bytes: bytes) -> str:
    """Codifica bytes de audio a formato base64."""
    try:
        return base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        logger.error(f"Error al codificar audio a base64: {e}")
        return ""

def create_error_response(message: str, status_code: int = 500) -> tuple[dict, int]:
    """Crea una respuesta JSON de error estándar."""
    return {"error": message, "status": "error"}, status_code
