from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
import logging
import datetime
from services.huggingface_service import verify_hf_connection

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def read_root():
    """Endpoint de prueba para verificar que el servidor está funcionando"""
    return {"status": "ok", "message": "Servidor funcionando correctamente"}

@router.get("/status")
async def get_status(is_connected: bool = Depends(verify_hf_connection)):
    """Endpoint para verificar el estado de la conexión con Hugging Face"""
    try:
        logger.info(f"Estado de conexión HF verificado: {'conectado' if is_connected else 'desconectado'}")
        return JSONResponse(
            status_code=200,
            content={
                "status": "connected" if is_connected else "disconnected",
                "message": "Conectado a Hugging Face" if is_connected else "Desconectado de Hugging Face",
                "api_version": "1.0", # Podría venir de un archivo de config
                "timestamp": str(datetime.datetime.now())
            }
        )
    except Exception as e:
        logger.error(f"Error inesperado al obtener el estado: {e}")
        # Devolver 200 para que el cliente pueda leer el error
        return JSONResponse(
            status_code=200, 
            content={
                "status": "error",
                "message": f"Error al verificar la conexión: {str(e)}",
                "error_type": str(type(e).__name__),
                "timestamp": str(datetime.datetime.now())
            }
        ) 