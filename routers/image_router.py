from fastapi import APIRouter, UploadFile, File, HTTPException
import logging
from typing import List
import io
from PIL import Image
import sys
import os

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import services and utilities
try:
    from ..services.image_service import analyze_image, process_sign_language
    from ..common.service_utils import load_and_validate_image
    from ..routes import PROCESS_IMAGE_ROUTE, ANALYZE_SIGN_LANGUAGE_ROUTE
    from ..utils import validate_image_magic_bytes
    from ..common.router_utils import handle_errors  # Centralized error handling
except ImportError:
    from services.image_service import analyze_image, process_sign_language
    from common.service_utils import load_and_validate_image
    from routes import PROCESS_IMAGE_ROUTE, ANALYZE_SIGN_LANGUAGE_ROUTE
    from utils import validate_image_magic_bytes
    from common.router_utils import handle_errors  # Centralized error handling
# Local ASL model removed in favor of gradio_client-only flow to reduce deps

# Configurar logging
logger = logging.getLogger(__name__)

# Tipos MIME permitidos para imágenes
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp"]

router = APIRouter(
    prefix="/api/image",
    tags=["imagen"],
    responses={404: {"description": "Recurso no encontrado"}}
)

@router.post(PROCESS_IMAGE_ROUTE)
@handle_errors
async def process_image(file: UploadFile = File(...)):
    """
    Procesa una imagen y detecta objetos/escenas
    """
    # Cargar y validar la imagen usando helper
    image = await load_and_validate_image(file, ALLOWED_IMAGE_TYPES)
    # Analizar la imagen
    result = await analyze_image(image)
    return {
        "objects": result.get("objects", []),
        "description": result.get("description", "No se pudo generar una descripción")
    }

@router.post(ANALYZE_SIGN_LANGUAGE_ROUTE)
@handle_errors
async def analyze_sign_language(file: UploadFile = File(...)):
    """
    Analiza una imagen de lenguaje de señas
    """
    # Cargar y validar la imagen usando helper
    image = await load_and_validate_image(file, ALLOWED_IMAGE_TYPES)
    # Analizar el lenguaje de señas
    return await process_sign_language(image)

@router.post("/asl/predict")
async def predict_asl(file: UploadFile = File(...)):
    """
    Predicción ASL usando exclusivamente la API de Gradio (sin modelo local).
    Alias de compatibilidad para el frontend antiguo.
    """
    try:
        # Validar tipo de archivo
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de archivo no soportado. Tipos permitidos: {ALLOWED_IMAGE_TYPES}"
            )

        # Cargar y validar la imagen
        image = await load_and_validate_image(file, ALLOWED_IMAGE_TYPES)

        # Procesar con el servicio optimizado de lenguaje de señas (gradio_client)
        result = await process_sign_language(image)

        return {
            "success": True,
            "prediction": result.get("resultado", "Sin reconocimiento"),
            "confidence": result.get("confianza", 0.0),
            "alternatives": result.get("alternativas", []),
            "message": "Imagen procesada exitosamente"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en predict_asl: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.post("/asl/predict_space")
async def predict_asl_space(file: UploadFile = File(...)):
    """
    Endpoint específico para el frontend - Recibe una imagen y retorna la predicción ASL.
    Utiliza la API de Gradio para el procesamiento optimizado.
    """
    try:
        # Validar tipo de archivo
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"Tipo de archivo no soportado. Tipos permitidos: {ALLOWED_IMAGE_TYPES}"
            )
        
        # Cargar y validar la imagen
        image = await load_and_validate_image(file, ALLOWED_IMAGE_TYPES)
        
        # Procesar con el servicio optimizado de lenguaje de señas
        result = await process_sign_language(image)
        
        return {
            "success": True,
            "prediction": result.get("resultado", "Sin reconocimiento"),
            "confidence": result.get("confianza", 0.0),
            "alternatives": result.get("alternativas", []),
            "message": "Imagen procesada exitosamente"
        }
        
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        logger.error(f"Error en predict_asl_space: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error interno del servidor: {str(e)}"
        )