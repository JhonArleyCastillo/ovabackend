from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
import logging
import datetime
import sys
import platform
import psutil
# Importar las rutas definidas
from backend.routes import STATUS_ROUTE
from backend.services.huggingface_service import HuggingFaceService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def read_root(request: Request):
    """Endpoint de prueba para verificar que el servidor está funcionando"""
    logger.info(f"Solicitud de raíz desde: {request.client.host}")
    return {
        "status": "ok", 
        "message": "Servidor funcionando correctamente",
        "timestamp": str(datetime.datetime.now())
    }

@router.get(STATUS_ROUTE)
async def get_status():
    """
    Devuelve información sobre el estado del servidor
    """
    return {
        "status": "online",
        "timestamp": datetime.datetime.now().isoformat(),
        "system": {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent
        }
    }