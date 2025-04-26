from fastapi import APIRouter, UploadFile, File, HTTPException
import logging
from typing import List
import io
from PIL import Image
# Cambiado a importaciones absolutas desde backend
from backend.services.image_service import analyze_image, process_sign_language
from backend.routes import PROCESS_IMAGE_ROUTE, ANALYZE_SIGN_LANGUAGE_ROUTE
from backend.utils import validate_image_magic_bytes

# Configurar logging
logger = logging.getLogger(__name__)

# Tipos MIME permitidos para imágenes
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp"]

router = APIRouter()

@router.post(PROCESS_IMAGE_ROUTE)
async def process_image(file: UploadFile = File(...)):
    """
    Procesa una imagen y detecta objetos/escenas
    """
    # Verificación inicial del tipo MIME declarado
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
    
    try:
        # Leer la imagen
        image_data = await file.read()
        
        # Validar el tipo de archivo con magic bytes
        is_valid, detected_type = validate_image_magic_bytes(image_data)
        
        if not is_valid:
            logger.warning(f"Imagen rechazada: magic bytes no válidos. Tipo declarado: {file.content_type}")
            raise HTTPException(status_code=400, detail="La extensión de la imagen no es permitida")
            
        if detected_type not in ALLOWED_IMAGE_TYPES:
            logger.warning(f"Imagen rechazada: tipo {detected_type} no está en la lista de permitidos")
            raise HTTPException(status_code=400, detail="La extensión de la imagen no es permitida")
            
        # Si hay discrepancia entre el tipo declarado y detectado, lo registramos pero continuamos
        if detected_type != file.content_type and file.content_type in ALLOWED_IMAGE_TYPES:
            logger.warning(f"Discrepancia de tipo: declarado {file.content_type} vs detectado {detected_type}")
        
        # Abrir la imagen con PIL
        image = Image.open(io.BytesIO(image_data))
        
        # Analizar la imagen
        result = await analyze_image(image)
        
        return {
            "objects": result.get("objects", []),
            "description": result.get("description", "No se pudo generar una descripción")
        }
    except HTTPException:
        # Reenviar las excepciones HTTP tal cual
        raise
    except Exception as e:
        logger.error(f"Error al procesar imagen: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar imagen: {str(e)}")

@router.post(ANALYZE_SIGN_LANGUAGE_ROUTE)
async def analyze_sign_language(file: UploadFile = File(...)):
    """
    Analiza una imagen de lenguaje de señas
    """
    # Verificación inicial del tipo MIME declarado
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
    
    try:
        # Leer la imagen
        image_data = await file.read()
        
        # Validar el tipo de archivo con magic bytes
        is_valid, detected_type = validate_image_magic_bytes(image_data)
        
        if not is_valid:
            logger.warning(f"Imagen de lenguaje de señas rechazada: magic bytes no válidos. Tipo declarado: {file.content_type}")
            raise HTTPException(status_code=400, detail="La extensión de la imagen no es permitida")
            
        if detected_type not in ALLOWED_IMAGE_TYPES:
            logger.warning(f"Imagen de lenguaje de señas rechazada: tipo {detected_type} no está en la lista de permitidos")
            raise HTTPException(status_code=400, detail="La extensión de la imagen no es permitida")
        
        # Abrir la imagen con PIL
        image = Image.open(io.BytesIO(image_data))
        
        # Analizar el lenguaje de señas
        result = await process_sign_language(image)
        
        return result
    except HTTPException:
        # Reenviar las excepciones HTTP tal cual
        raise  
    except Exception as e:
        logger.error(f"Error al procesar lenguaje de señas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar la imagen de lenguaje de señas: {str(e)}")