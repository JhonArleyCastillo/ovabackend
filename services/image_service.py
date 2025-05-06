import logging
import numpy as np
# Cambiado a importación relativa
from .huggingface_service import hf_client
import cv2 # Asegurarse que cv2 está importado
from PIL import Image

# Importar modelos desde config
from backend.config import HF_MODELO_SIGN

logger = logging.getLogger(__name__)

# Usar variables de entorno para los modelos
DEFAULT_SIGN_LANGUAGE_MODEL = HF_MODELO_SIGN  # Usa el modelo específico de señas
# Para modelos no definidos en .env, mantener valores por defecto
DEFAULT_OBJECT_DETECTION_MODEL = "facebook/detr-resnet-50"  # Ejemplo
DEFAULT_IMAGE_CAPTIONING_MODEL = "nlpconnect/vit-gpt2-image-captioning"  # Ejemplo

async def analyze_image(image: Image.Image) -> dict:
    """
    Función principal para analizar una imagen.
    Detecta objetos y genera una descripción.
    
    Args:
        image: Imagen PIL a analizar
    
    Returns:
        dict: Resultados del análisis con objetos detectados y descripción
    """
    # Convertir imagen PIL a numpy array para procesamiento
    np_image = np.array(image)
    
    # Detectar objetos en la imagen
    objects = detect_objects(np_image)
    
    # Convertir la imagen a bytes para el proceso de captioning
    img_byte_arr = cv2.imencode('.jpg', np_image)[1].tobytes()
    
    # Obtener descripción de la imagen
    description_result = describe_image_captioning(img_byte_arr)
    
    # Preparar respuesta
    result = {
        "objects": objects if isinstance(objects, list) else [],
        "description": description_result.get("descripcion", "No se pudo generar una descripción")
    }
    
    return result

async def process_sign_language(image: Image.Image) -> dict:
    """
    Procesa una imagen de lenguaje de señas y devuelve la interpretación.
    
    Args:
        image: Imagen PIL de lenguaje de señas
    
    Returns:
        dict: Resultado del reconocimiento de señas
    """
    # Convertir imagen PIL a numpy array para procesamiento
    np_image = np.array(image)
    
    # Reconocer el lenguaje de señas en la imagen
    result = recognize_sign_language(np_image)
    
    return result

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