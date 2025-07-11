from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
import logging
import datetime
import sys
import platform
import psutil
import os

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import routes and services
from routes import STATUS_ROUTE
from services.huggingface_service import HuggingFaceService
from common.router_utils import handle_errors

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
@handle_errors
async def read_root(request: Request):
    """Endpoint de prueba para verificar que el servidor está funcionando"""
    logger.info(f"Solicitud de raíz desde: {request.client.host}")
    return {
        "status": "ok", 
        "message": "Servidor funcionando correctamente",
        "timestamp": str(datetime.datetime.now())
    }

@router.get(STATUS_ROUTE)
@handle_errors
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