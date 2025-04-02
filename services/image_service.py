import logging
import numpy as np
from services.huggingface_service import hf_client
import cv2 # Asegurarse que cv2 está importado

logger = logging.getLogger(__name__)

# Reemplazar con los nombres reales de los modelos que estás usando
DEFAULT_SIGN_LANGUAGE_MODEL = "facebook/wav2vec2-large-xlsr-53-spanish-with-lm" # Ejemplo
DEFAULT_OBJECT_DETECTION_MODEL = "facebook/detr-resnet-50" # Ejemplo
DEFAULT_IMAGE_CAPTIONING_MODEL = "nlpconnect/vit-gpt2-image-captioning" # Ejemplo

def recognize_sign_language(image: np.ndarray) -> dict:
    """Reconoce lenguaje de señas en una imagen."""
    try:
        client = hf_client()
        # Aquí iría la lógica real para llamar al modelo
        # _, img_encoded = cv2.imencode('.jpg', image)
        # image_bytes = img_encoded.tobytes()
        # response = client.image_classification(image_bytes, model=DEFAULT_SIGN_LANGUAGE_MODEL)
        
        # Simulación
        response = [{'label': 'A', 'score': 0.95}, {'label': 'Hola', 'score': 0.03}]
        
        if not response:
            raise ValueError("La respuesta del modelo de señas está vacía")

        main_prediction = response[0]
        alternatives_raw = response[1:]
        
        alternatives = [
            {"simbolo": alt['label'], "probabilidad": round(alt['score'] * 100, 2)}
            for alt in alternatives_raw
        ]

        result = {
            "resultado": main_prediction['label'],
            "confianza": round(main_prediction['score'] * 100, 2),
            "alternativas": alternatives
        }
        logger.info(f"Lenguaje de señas reconocido: {result['resultado']}")
        return result
    except Exception as e:
        logger.error(f"Error al reconocer lenguaje de señas: {e}")
        return {"error": f"Error en el análisis de señas: {str(e)}"}

def detect_objects(image: np.ndarray) -> list | dict:
    """Detecta objetos en una imagen."""
    try:
        client = hf_client()
        # Lógica real para llamar al modelo
        # _, img_encoded = cv2.imencode('.jpg', image)
        # image_bytes = img_encoded.tobytes()
        # response = client.object_detection(image_bytes, model=DEFAULT_OBJECT_DETECTION_MODEL)

        # Simulación
        response = [
            {"score": 0.98, "label": "gato", "box": {"xmin": 10, "ymin": 20, "xmax": 100, "ymax": 120}},
            {"score": 0.91, "label": "sofá", "box": {"xmin": 50, "ymin": 50, "xmax": 200, "ymax": 150}}
        ]
        
        logger.info(f"Detectados {len(response)} objetos.")
        # Asegurarse de devolver siempre una lista en caso de éxito
        return response if isinstance(response, list) else []
    except Exception as e:
        logger.error(f"Error al detectar objetos: {e}")
        return {"error": f"Error en detección de objetos: {str(e)}"}

def describe_image_captioning(image_bytes: bytes) -> dict:
    """Genera una descripción para una imagen."""
    try:
        client = hf_client()
        # Lógica real para llamar al modelo
        response = client.image_to_text(image_bytes, model=DEFAULT_IMAGE_CAPTIONING_MODEL)
        
        # response = [{'generated_text': 'Un gato sentado en un sofá.'}] # Simulación
        if not response or not isinstance(response, list) or not response[0].get('generated_text'):
             raise ValueError("Respuesta inválida del modelo de captioning")

        description = response[0]['generated_text']
        
        logger.info("Descripción de imagen generada.")
        return {"descripcion": description}
    except Exception as e:
        logger.error(f"Error al describir la imagen: {e}")
        return {"error": f"Error en descripción de imagen: {str(e)}"}

# Funciones legacy eliminadas
# reconocer_lenguaje_senas = recognize_sign_language
# detectar_objetos = detect_objects
# describir_imagen = describe_image_captioning 