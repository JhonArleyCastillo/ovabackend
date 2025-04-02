from fastapi import APIRouter, Depends, Body, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any
from services.image_service import recognize_sign_language, detect_objects, describe_image_captioning
from services.huggingface_service import verify_hf_connection
from utils import decode_base64_image, create_error_response
import base64
import numpy as np
import cv2 # Importar cv2

logger = logging.getLogger(__name__)
router = APIRouter()

# Dependencia para verificar la conexión a HF y la imagen
def verify_hf_and_decode_image(payload: Dict[str, Any] = Body(...), 
                                is_connected: bool = Depends(verify_hf_connection)) -> np.ndarray:
    """Dependencia que verifica conexión HF y decodifica la imagen del payload."""
    if not is_connected:
        logger.error("Intento de análisis de imagen sin conexión a Hugging Face.")
        # Usamos 200 para que el frontend pueda leer el error fácilmente
        raise HTTPException(status_code=200, detail=create_error_response("API key de Hugging Face no configurada o inválida", 200)[0])

    base64_image = payload.get("image")
    if not base64_image:
        raise HTTPException(status_code=400, detail=create_error_response("No se proporcionó ninguna imagen", 400)[0])

    img = decode_base64_image(base64_image)
    if img is None:
        raise HTTPException(status_code=400, detail=create_error_response("Formato de imagen inválido o no decodificable", 400)[0])
        
    return img

@router.post("/analyze-sign-language")
async def analyze_sign_language_endpoint(img: np.ndarray = Depends(verify_hf_and_decode_image)):
    """Endpoint para analizar lenguaje de señas en una imagen."""
    try:
        logger.info("Procesando imagen para análisis de lenguaje de señas")
        resultado = recognize_sign_language(img)
        
        if "error" in resultado:
            logger.error(f"Error en análisis de señas: {resultado['error']}")
            # Devolver 200 OK con el error en el cuerpo
            return JSONResponse(status_code=200, content=resultado)
        
        logger.info(f"Análisis de señas exitoso: {resultado.get('resultado', 'N/A')}")
        return {
            "prediction": resultado.get("resultado"),
            "confidence": resultado.get("confianza"),
            "alternatives": resultado.get("alternativas", []),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error inesperado en endpoint analyze-sign-language: {e}")
        # Devolver 200 OK con el error en el cuerpo
        return JSONResponse(status_code=200, 
                            content=create_error_response(f"Error interno al analizar la imagen: {str(e)}", 200)[0])

@router.post("/detect-objects")
async def detect_objects_endpoint(img: np.ndarray = Depends(verify_hf_and_decode_image)):
    """Endpoint para detectar objetos en una imagen."""
    try:
        logger.info("Procesando imagen para detección de objetos")
        resultado = detect_objects(img)
        
        if isinstance(resultado, dict) and "error" in resultado:
            logger.error(f"Error en detección de objetos: {resultado['error']}")
            return JSONResponse(status_code=500, content=resultado) # 500 podría ser apropiado aquí
        
        logger.info(f"Detección de objetos exitosa: {len(resultado)} objetos encontrados")
        return {
            "objects": resultado,
            "count": len(resultado),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error inesperado en endpoint detect-objects: {e}")
        return JSONResponse(status_code=500, 
                            content=create_error_response(f"Error interno al detectar objetos: {str(e)}", 500)[0])

@router.post("/describe-image")
async def describe_image_endpoint(payload: Dict[str, Any] = Body(...),
                                is_connected: bool = Depends(verify_hf_connection)):
    """Endpoint para generar descripción de una imagen."""
    # No usamos la dependencia de decodificación aquí porque necesitamos los bytes
    if not is_connected:
        logger.error("Intento de descripción de imagen sin conexión a Hugging Face.")
        raise HTTPException(status_code=200, detail=create_error_response("API key de Hugging Face no configurada o inválida", 200)[0])

    try:
        base64_image = payload.get("image", "")
        if not base64_image:
             raise HTTPException(status_code=400, detail=create_error_response("No se proporcionó ninguna imagen", 400)[0])

        if "base64," in base64_image:
            base64_image = base64_image.split("base64,")[1]
        image_bytes = base64.b64decode(base64_image)

    except Exception as e:
         raise HTTPException(status_code=400, detail=create_error_response(f"Error al decodificar imagen: {e}", 400)[0])

    try:
        logger.info("Procesando imagen para generación de descripción")
        resultado = describe_image_captioning(image_bytes)
        
        if "error" in resultado:
            logger.error(f"Error en descripción de imagen: {resultado['error']}")
            return JSONResponse(status_code=500, content=resultado)
        
        logger.info("Descripción de imagen generada correctamente")
        return {
            "description": resultado.get("descripcion"),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error inesperado en endpoint describe-image: {e}")
        return JSONResponse(status_code=500, 
                            content=create_error_response(f"Error interno al generar descripción: {str(e)}", 500)[0])

@router.post("/process-image")
async def process_image_endpoint(file: UploadFile = File(...),
                                 is_connected: bool = Depends(verify_hf_connection)):
    """Endpoint genérico para procesar una imagen: detecta objetos y genera descripción."""
    if not is_connected:
        logger.error("Intento de análisis de imagen sin conexión a Hugging Face.")
        raise HTTPException(status_code=200, detail=create_error_response("API key de Hugging Face no configurada o inválida", 200)[0])

    description_result = None
    objects_result = []
    error_occurred = False
    error_message = "Error procesando la imagen"

    try:
        logger.info(f"Recibido archivo de imagen: {file.filename}")
        image_bytes = await file.read()
        
        # Decodificar imagen para detección de objetos
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            logger.error("Error al decodificar imagen para análisis combinado")
            raise HTTPException(status_code=400, detail=create_error_response("Formato de imagen inválido para análisis", 400)[0])

        # 1. Obtener descripción
        try:
            logger.info("Llamando a servicio de descripción...")
            resultado_desc = describe_image_captioning(image_bytes)
            if "error" in resultado_desc:
                logger.error(f"Error parcial en descripción: {resultado_desc['error']}")
                # Podríamos continuar o fallar aquí, decidimos continuar pero registrar
                description_result = f"Error: {resultado_desc['error']}"
            else:
                description_result = resultado_desc.get("descripcion", "Descripción no disponible")
                logger.info("Descripción obtenida.")
        except Exception as desc_e:
            logger.error(f"Excepción en servicio de descripción: {desc_e}")
            description_result = "Error al generar descripción"
            # Marcar error pero continuar con detección de objetos si es posible

        # 2. Detectar objetos
        try:
            logger.info("Llamando a servicio de detección de objetos...")
            resultado_obj = detect_objects(img)
            if isinstance(resultado_obj, dict) and "error" in resultado_obj:
                logger.error(f"Error parcial en detección de objetos: {resultado_obj['error']}")
                objects_result = [{"error": resultado_obj['error']}] 
            else:
                # Asegurarnos que sea una lista (como se espera)
                objects_result = resultado_obj if isinstance(resultado_obj, list) else []
                logger.info(f"Detección de objetos completada ({len(objects_result)} encontrados)." )
        except Exception as obj_e:
            logger.error(f"Excepción en servicio de detección de objetos: {obj_e}")
            objects_result = [{"error": "Error al detectar objetos"}]
        
        logger.info("Análisis combinado de imagen completado.")
        return {
            "status": "success",
            "descripcion": description_result,
            "objetos_detectados": objects_result
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error inesperado en endpoint /process-image: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=create_error_response(f"Error interno al procesar la imagen: {str(e)}", 500)[0]
        ) 