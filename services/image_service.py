"""
Servicio de procesamiento de imágenes - El corazón del reconocimiento ASL.

Este módulo maneja todo lo relacionado con el análisis de imágenes:
- Reconocimiento de lenguaje de señas (lo más importante)
- Detección de objetos generales 
- Generación de descripciones de imágenes

Como desarrollador fullstack, aquí es donde ocurre la magia de conectar
con Gradio Spaces para el reconocimiento ASL. Si algo falla con ASL,
probablemente sea aquí donde necesitas buscar.
"""

import logging
import json
import time
from typing import Dict, List, Any, Optional, Union
import numpy as np
import asyncio
# Nota: Removimos OpenCV para optimizar en EC2, usamos PIL que es más ligero

from PIL import Image

import sys
import os

# Agregamos el directorio padre para imports relativos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from .huggingface_service import hf_client, hf_client_async
from .resilience_service import ResilienceService
from .gradio_compatibility_service import gradio_service

HF_ASL_SPACE_URL: Optional[str] = os.getenv(
    "HF_ASL_SPACE_URL",
    "https://jhonarleycastillov-asl-image.hf.space"
)
# Logger para este módulo
logger = logging.getLogger(__name__)

# Modelos por defecto que usamos
# NOTA: Eliminado DEFAULT_SIGN_LANGUAGE_MODEL basado en HF_MODELO_SIGN.
# El reconocimiento ASL se hace vía Space (HF_ASL_SPACE_URL) manejado por
# GradioCompatibilityService, no por modelo directo.
DEFAULT_OBJECT_DETECTION_MODEL = "facebook/detr-resnet-50"
DEFAULT_IMAGE_CAPTIONING_MODEL = "nlpconnect/vit-gpt2-image-captioning"

@ResilienceService.resilient_hf_call(
    timeout_seconds=60.0,
    retry_attempts=3,
    fallback_response={
        "objects": [], 
        "description": "Servicio de análisis de imágenes temporalmente no disponible"
    }
)
async def analyze_image_async(image: Image.Image) -> Dict[str, Any]:
    """Analiza una imagen de forma completa aplicando patrones de resiliencia.

    Esta es la función "todo en uno" para análisis general de imágenes:
    - Detecta objetos presentes (lista simulada / placeholder actualmente)
    - Genera una breve descripción en lenguaje natural
    - Aplica reintentos y fallback automático si algo falla

    Parámetros:
        image (PIL.Image): Imagen PIL a analizar.

    Retorna:
        dict: Resultado con dos claves principales:
            - objects: Lista de objetos detectados (puede venir vacía)
            - description: Descripción generada de la escena

    Lanza:
        ValueError: Si la imagen viene vacía o con formato inválido.
        RuntimeError: Si todos los intentos de análisis fallan.
    """
    if image is None:
        raise ValueError("La imagen no puede ser None")
        
    try:
        # Convertimos la imagen PIL a numpy para los modelos de visión
        np_image = np.array(image)
        
        if np_image.size == 0:
            raise ValueError("La matriz de imagen está vacía")
        
        # Detectamos objetos (implementación simulada actualmente)
        objects = await detect_objects_async(np_image)
        
        # Convertimos la imagen a bytes para el modelo de captioning (sin OpenCV)
        import io
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # Generamos descripción de la imagen
        description_result = await describe_image_captioning_async(img_byte_arr)
        
        # Construimos respuesta estructurada y segura
        result = {
            "objects": objects if isinstance(objects, list) else [],
            "description": description_result.get(
                "descripcion", 
                "No se pudo generar una descripción de la imagen"
            )
        }
        
        logger.info(f"Análisis de imagen completado: {len(result['objects'])} objetos detectados")
        return result
        
    except Exception as e:
        logger.error(f"Error en análisis de imagen: {str(e)}")
        raise RuntimeError(f"Fallo el análisis de imagen: {str(e)}")

async def analyze_image(image: Image.Image) -> dict:
    """
    Función principal para analizar imágenes generales (no ASL).
    
    Esto detecta objetos como gatos, carros, etc. y genera descripciones.
    Para reconocimiento ASL, usa process_sign_language() en su lugar.
    
    Args:
        image: Imagen PIL a analizar
    
    Returns:
        dict: Resultados con objetos detectados y descripción textual
    """
    # Convertimos imagen PIL a numpy array (formato que espera el detector)
    np_image = np.array(image)
    
    # Detectamos objetos en la imagen
    objects = detect_objects(np_image)
    
    # Convertimos la imagen a bytes para el modelo de descripción
    import io
    img_byte_arr = io.BytesIO()
    # Convertimos numpy array de vuelta a PIL Image
    pil_image = Image.fromarray(np_image)
    pil_image.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()
    
    # Generamos descripción textual de la imagen
    description_result = describe_image_captioning(img_byte_arr)
    
    # Preparamos respuesta estructurada
    result = {
        "objects": objects if isinstance(objects, list) else [],
        "description": description_result.get("descripcion", "No se pudo generar una descripción")
    }
    
    return result

async def process_sign_language(image: Image.Image, correlation_id: str | None = None) -> dict:
    """
    ¡LA FUNCIÓN PRINCIPAL PARA ASL! 
    
    Esta función procesa imágenes de lenguaje de señas usando el nuevo servicio robusto
    de compatibilidad que maneja las diferencias entre entornos local y producción.
    
    Args:
        image: Imagen PIL que contiene un signo ASL
        correlation_id: ID para seguimiento en logs (opcional)
    
    Returns:
        dict: Resultado del reconocimiento con 'resultado', 'confianza', 'alternativas'
        
    Nota: Ahora usa GradioCompatibilityService para manejo robusto de fallbacks
    """
    prefix = f"[ASL_MAIN][{correlation_id}]" if correlation_id else "[ASL_MAIN]"
    logger.info(f"{prefix} 🎯 Iniciando procesamiento ASL con servicio robusto")
    
    try:
        # Validaciones básicas de la imagen
        if image is None:
            logger.error(f"{prefix} ❌ Imagen es None")
            return {
                "resultado": "Error: imagen vacía",
                "confianza": 0.0,
                "alternativas": [],
                "error": "Imagen no proporcionada"
            }
        
        # Verificar que la imagen tiene contenido
        if hasattr(image, 'size') and (image.size[0] == 0 or image.size[1] == 0):
            logger.error(f"{prefix} ❌ Imagen tiene dimensiones inválidas: {image.size}")
            return {
                "resultado": "Error: imagen inválida",
                "confianza": 0.0,
                "alternativas": [],
                "error": f"Dimensiones inválidas: {image.size}"
            }
        
        logger.debug(f"{prefix} ✅ Imagen válida: {image.format if hasattr(image, 'format') else 'formato desconocido'} - {image.size}")
        
        # Usar el servicio de compatibilidad robusto
        result = gradio_service.get_asl_prediction(image, correlation_id)
        
        logger.info(f"{prefix} 🎯 Resultado ASL: '{result.get('resultado', 'N/A')}' confianza: {result.get('confianza', 0)}%")
        
        return result
        
    except Exception as e:
        logger.error(f"{prefix} ❌ Error crítico en procesamiento ASL: {e}")
        return {
            "resultado": "Error del sistema",
            "confianza": 0.0,
            "alternativas": [],
            "error": str(e)
        }

def recognize_sign_language(image: np.ndarray, correlation_id: str | None = None) -> dict:
    """
    [DEPRECATED] Wrapper legacy que mantiene compatibilidad con código existente.

    Ahora se delega toda la lógica al nuevo servicio robusto GradioCompatibilityService.
    Se mantiene temporalmente para no romper importaciones y facilitar rollback.

    Args:
        image: Imagen en numpy array
        correlation_id: ID de correlación para logs

    Returns:
        dict con resultado del reconocimiento
    """
    prefix = f"[ASL_WRAPPER][{correlation_id}]" if correlation_id else "[ASL_WRAPPER]"
    logger.debug(f"{prefix} Delegando a GradioCompatibilityService (legacy wrapper)")
    try:
        # Convertimos a PIL si viene como numpy
        pil_image = Image.fromarray(image).convert("RGB") if isinstance(image, np.ndarray) else image
        return gradio_service.get_asl_prediction(pil_image, correlation_id)
    except Exception as e:
        logger.error(f"{prefix} Error en wrapper legacy: {e}")
        return {
            "resultado": "Error en wrapper",
            "confianza": 0.0,
            "alternativas": [],
            "error": str(e)
        }

def detect_objects(image: np.ndarray) -> list | dict:
    """Detecta objetos en una imagen (implementación simulada placeholder)."""
    try:
        client = hf_client()
        # Convert PIL image to bytes for model processing
        # Real object detection logic would go here using PIL
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
    """Detecta objetos en una imagen de forma asíncrona (placeholder)."""
    try:
        client = await hf_client_async()
        # Convert PIL image to bytes for model processing
        # Real async object detection logic would go here using PIL
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
    """Genera una descripción para una imagen de forma asíncrona."""
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
    """Genera una descripción para una imagen (versión síncrona)."""
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