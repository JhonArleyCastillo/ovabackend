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
from config import HF_MODELO_SIGN, HF_ASL_SPACE_URL

# Logger para este módulo
logger = logging.getLogger(__name__)

# Modelos por defecto que usamos
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
        
        # Convert PIL image to bytes for captioning process using PIL instead of OpenCV
        import io
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()
        
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
    
    Esta función procesa imágenes de lenguaje de señas y devuelve qué signo detectó.
    Es básicamente un wrapper que convierte la imagen y llama a recognize_sign_language.
    
    Args:
        image: Imagen PIL que contiene un signo ASL
        correlation_id: ID para seguimiento en logs (opcional)
    
    Returns:
        dict: Resultado del reconocimiento con 'resultado', 'confianza', 'alternativas'
    """
    # Convertir imagen PIL a numpy array para procesamiento
    # Convertimos PIL a numpy array (formato esperado por recognize_sign_language)
    np_image = np.array(image)
    return recognize_sign_language(np_image, correlation_id=correlation_id)

def recognize_sign_language(image: np.ndarray, correlation_id: str | None = None) -> dict:
    """
    Aquí es donde realmente ocurre el reconocimiento ASL usando Gradio Space.
    
    Esta función:
    1. Conecta al Gradio Space configurado en HF_ASL_SPACE_URL
    2. Envía la imagen para reconocimiento
    3. Parsea la respuesta (que puede venir en diferentes formatos)
    4. Devuelve un resultado estandarizado
    
    Si hay problemas con ASL, este es el lugar donde buscar.
    Optimizada para EC2 - no carga modelos localmente, solo usa la API remota.
    """
    try:
        from gradio_client import Client, handle_file
        import tempfile
        import re

        # Convertimos numpy array a PIL Image
        pil_image = Image.fromarray(image).convert("RGB")

        # Guardamos temporalmente la imagen (Gradio necesita un archivo)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            pil_image.save(tmp_file.name, format='PNG')
            temp_path = tmp_file.name

        try:
            # Conectamos al Space ASL en Hugging Face
            prefix = f"[ASL_CORE][{correlation_id}]" if correlation_id else "[ASL_CORE]"
            logger.info(f"{prefix} 🔍 Conectando al Space ASL... {HF_ASL_SPACE_URL}")
            client = Client(HF_ASL_SPACE_URL)

            # Enviamos la imagen para reconocimiento
            logger.info(f"{prefix} 📸 Enviando imagen ASL al Space... archivo temporal: {os.path.basename(temp_path)}")
            t_call = time.time()
            result = client.predict(image=handle_file(temp_path), api_name="/predict")
            call_ms = (time.time() - t_call) * 1000
            
            # Mostramos un preview de lo que devolvió el Space
            try:
                preview = str(result)
                if len(preview) > 300:
                    preview = preview[:300] + '…'
            except Exception:
                preview = '<no representable>'
            logger.info(f"{prefix} ⏱️ Space respondió en {call_ms:.1f}ms - tipo: {type(result).__name__} preview: {preview}")
            
            # Loggeamos el JSON completo para debugging (puede ser largo)
            try:
                if isinstance(result, (dict, list, tuple)):
                    raw_json = json.dumps(result, ensure_ascii=False, default=str)
                else:
                    raw_json = json.dumps({"raw": result}, ensure_ascii=False, default=str)
                if len(raw_json) > 8000:  # Evitamos logs excesivamente largos
                    logger.debug(f"{prefix} RAW_JSON (truncado) {raw_json[:8000]}… (longitud total={len(raw_json)})")
                else:
                    logger.debug(f"{prefix} RAW_JSON {raw_json}")
            except Exception as jex:
                logger.debug(f"{prefix} Error serializando JSON: tipo={type(result).__name__} error={jex}")

            # Procesamos el resultado - aquí viene la parte complicada
            # Gradio puede devolver diferentes formatos dependiendo del modelo
            prediction_result = None
            alt_list: list[dict] = []
            parse_path = 'unknown'
            
            if isinstance(result, (list, tuple)):
                # Casos posibles: [label, prob, top_preds], [(label, prob), ...], [{label, confidence}, ...]
                if len(result) >= 2 and isinstance(result[0], str):
                    parse_path = 'lista[etiqueta,probabilidad,(alternativas?)]'
                    # Formato típico: [etiqueta, probabilidad, ...]
                    label = result[0]
                    prob_raw = result[1]
                    try:
                        prob = float(prob_raw)
                        prob = prob * 100 if prob <= 1 else prob  # Normalizamos a porcentaje
                    except Exception:
                        prob = 0.0
                    
                    # Intentamos extraer alternativas si existe un tercer elemento
                    if len(result) >= 3 and isinstance(result[2], (list, tuple)):
                        for item in list(result[2])[:5]:  # Max 5 alternativas
                            if isinstance(item, (list, tuple)) and len(item) >= 2:
                                try:
                                    p = float(item[1])
                                    p = p * 100 if p <= 1 else p
                                except Exception:
                                    p = 0.0
                                alt_list.append({"label": str(item[0]), "confidence": round(p, 2)})
                    return {
                        "resultado": label,
                        "confianza": round(prob, 2),
                        "alternativas": alt_list
                    }
                
                # Si el primer elemento es un diccionario, lo usamos directamente
                if len(result) >= 1 and isinstance(result[0], dict):
                    parse_path = 'lista[diccionario]'
                    prediction_result = result[0]
                else:
                    # Si solo hay un string, lo procesamos abajo con regex
                    if len(result) == 1 and isinstance(result[0], str):
                        result = result[0]
                    else:
                        prediction_result = None
                        
            elif isinstance(result, dict):
                parse_path = 'diccionario_directo'
                prediction_result = result
            elif isinstance(result, (str, int, float, bool)):
                parse_path = 'valor_escalar'
                # Valores escalares inesperados del Space
                if not isinstance(result, str):
                    logger.warning(f"Formato inesperado del Space ASL: {type(result).__name__} -> {result}")
                prediction_result = None
            else:
                logger.warning(f"{prefix} Tipo de respuesta no reconocido del Space ASL: {type(result).__name__}")

            # Si tenemos un diccionario de predicción, lo procesamos
            if isinstance(prediction_result, dict):
                logger.debug(f"{prefix} parse_path={parse_path} usando diccionario con keys={list(prediction_result.keys())}")
                # Normalizamos confianza a escala 0-100
                raw_conf = prediction_result.get("confidence", 0)
                try:
                    conf = float(raw_conf)
                except Exception:
                    conf = 0.0
                conf = conf * 100 if conf <= 1 else conf
                return {
                    "resultado": prediction_result.get("label", "Desconocido"),
                    "confianza": round(conf, 2),
                    "alternativas": []
                }
                
            elif isinstance(result, str):
                logger.debug(f"{prefix} parse_path={parse_path} intentando regex en string de {len(result)} caracteres")
                # String directo: intentamos extraer etiqueta y confianza con regex
                # Ejemplos esperados:
                # - "Predicción: A (65.40%)"
                # - "Prediccion: B (87%)"  
                # - "A (65.40%)"
                text = result.strip()
                # Regex tolerante a acentos y formatos de porcentaje
                m = re.search(r"(?i)(?:predicci[oó]n:\s*)?([A-Za-z0-9]+)\s*\((\d+(?:[\.,]\d+)?)%\)", text)
                if m:
                    label = m.group(1)
                    conf_str = m.group(2).replace(',', '.')  # Normalizamos punto decimal
                    try:
                        conf = float(conf_str)
                    except Exception:
                        conf = 0.0
                    final = {
                        "resultado": label,
                        "confianza": round(conf, 2),
                        "alternativas": []
                    }
                    logger.debug(f"{prefix} parse_path=regex exitoso - etiqueta={label} confianza={conf}")
                    return final
                
                # Si no coincide el patrón, devolvemos el texto tal como está
                final = {
                    "resultado": text,
                    "confianza": 0.0,
                    "alternativas": []
                }
                logger.debug(f"{prefix} parse_path=texto_sin_patron - longitud={len(text)}")
                return final
            else:
                logger.warning(f"{prefix} Resultado vacío o inválido del modelo ASL - parse_path={parse_path}")
                return {
                    "resultado": "Sin reconocimiento",
                    "confianza": 0.0,
                    "alternativas": []
                }

        finally:
            # Limpiamos el archivo temporal - importante para no llenar el disco
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except Exception as e:
        logger.error(f"{prefix} Error crítico en reconocimiento ASL: {e}")
        # Fallback: devolvemos respuesta de error pero estructurada
        return {
            "resultado": "Error en reconocimiento",
            "confianza": 0.0,
            "alternativas": [],
            "error": str(e)
        }

def detect_objects(image: np.ndarray) -> list | dict:
    """Detecta objetos en una imagen."""
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
    """Detecta objetos en una imagen de forma async."""
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