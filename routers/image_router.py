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
from services.image_service import analyze_image, process_sign_language
from common.service_utils import load_and_validate_image
from routes import PROCESS_IMAGE_ROUTE, ANALYZE_SIGN_LANGUAGE_ROUTE
from utils import validate_image_magic_bytes
from common.router_utils import handle_errors  # Centralized error handling

# Configurar logging
logger = logging.getLogger(__name__)

# Tipos MIME permitidos para imágenes
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp"]

router = APIRouter()

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