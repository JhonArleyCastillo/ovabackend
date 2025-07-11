"""
Image processing and analysis service module.

This module provides comprehensive image analysis capabilities including
object detection, image captioning, and sign language recognition using
Hugging Face models with built-in resilience patterns.
"""

import logging
from typing import Dict, List, Any, Optional, Union
import numpy as np
import asyncio
import cv2
from PIL import Image

import sys
import os

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from .huggingface_service import hf_client, hf_client_async
from .resilience_service import ResilienceService
from config import HF_MODELO_SIGN

# Configure module logger
logger = logging.getLogger(__name__)

# Model configuration constants
DEFAULT_SIGN_LANGUAGE_MODEL = HF_MODELO_SIGN
DEFAULT_OBJECT_DETECTION_MODEL = "facebook/detr-resnet-50"
DEFAULT_IMAGE_CAPTIONING_MODEL = "nlpconnect/vit-gpt2-image-captioning"

@ResilienceService.resilient_hf_call(
    timeout_seconds=60.0,
    retry_attempts=3,
    fallback_response={
        "objects": [], 
        "description": "Image analysis service temporarily unavailable"
    }
)
async def analyze_image_async(image: Image.Image) -> Dict[str, Any]:
    """
    Main function for comprehensive image analysis with resilience patterns.
    
    Performs object detection and generates image descriptions using multiple
    AI models with automatic fallback and retry mechanisms.
    
    Args:
        image (Image.Image): PIL Image object to analyze.
    
    Returns:
        Dict[str, Any]: Analysis results containing detected objects and 
                       image description.
                       
    Raises:
        ValueError: If image is None or invalid format.
        RuntimeError: If all analysis attempts fail.
    """
    if image is None:
        raise ValueError("Image cannot be None")
        
    try:
        # Convert PIL image to numpy array for processing
        np_image = np.array(image)
        
        if np_image.size == 0:
            raise ValueError("Image array is empty")
        
        # Detect objects in the image using computer vision models
        objects = await detect_objects_async(np_image)
        
        # Convert image to bytes for captioning process
        img_byte_arr = cv2.imencode('.jpg', np_image)[1].tobytes()
        
        # Generate image description using captioning models
        description_result = await describe_image_captioning_async(img_byte_arr)
        
        # Prepare structured response
        result = {
            "objects": objects if isinstance(objects, list) else [],
            "description": description_result.get(
                "descripcion", 
                "Could not generate image description"
            )
        }
        
        logger.info(f"Image analysis completed: {len(result['objects'])} objects detected")
        return result
        
    except Exception as e:
        logger.error(f"Error in image analysis: {str(e)}")
        raise RuntimeError(f"Image analysis failed: {str(e)}")
    
    return result

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
        # Lógica real para llamar al modelo
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

@ResilienceService.simple_retry(attempts=2, delay=1.0)
async def detect_objects_async(image: np.ndarray) -> list | dict:
    """Detecta objetos en una imagen de forma async."""
    try:
        client = await hf_client_async()
        # Lógica real para llamar al modelo
        # _, img_encoded = cv2.imencode('.jpg', image)
        # image_bytes = img_encoded.tobytes()
        # response = await asyncio.get_event_loop().run_in_executor(
        #     None, lambda: client.object_detection(image_bytes, model=DEFAULT_OBJECT_DETECTION_MODEL)
        # )

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
        raise  # Relanzar para que el sistema de resiliencia lo maneje

@ResilienceService.simple_retry(attempts=2, delay=1.0)
async def describe_image_captioning_async(image_bytes: bytes) -> dict:
    """Genera una descripción para una imagen de forma async."""
    try:
        client = await hf_client_async()
        # Lógica real para llamar al modelo
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: client.image_to_text(image_bytes, model=DEFAULT_IMAGE_CAPTIONING_MODEL)
        )
        
        # response = [{'generated_text': 'Un gato sentado en un sofá.'}] # Simulación
        if not response or not isinstance(response, list) or not response[0].get('generated_text'):
             raise ValueError("Respuesta inválida del modelo de captioning")

        description = response[0]['generated_text']
        
        logger.info("Descripción de imagen generada.")
        return {"descripcion": description}
    except Exception as e:
        logger.error(f"Error al describir la imagen: {e}")
        raise  # Relanzar para que el sistema de resiliencia lo maneje

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