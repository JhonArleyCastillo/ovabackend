"""
Middleware de captura de errores específicos de Gradio.

Este módulo proporciona un middleware para FastAPI que captura y maneja
específicamente el error "bool is not iterable" que ocurre con Gradio.
"""

import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

class GradioErrorMiddleware(BaseHTTPMiddleware):
    """
    Middleware que captura y maneja errores específicos de Gradio.
    Especialmente útil para el error "bool is not iterable".
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Procesa una solicitud y captura errores de Gradio.
        
        Args:
            request: Solicitud HTTP de FastAPI
            call_next: Siguiente middleware o endpoint
            
        Returns:
            Response: Respuesta HTTP apropiada
        """
        try:
            # Procesar la solicitud normalmente
            return await call_next(request)
            
        except TypeError as e:
            # Capturar específicamente errores de tipo bool no iterable
            error_msg = str(e).lower()
            if "bool" in error_msg and "iterable" in error_msg:
                logger.error(f"🚨 Interceptado error Gradio 'bool is not iterable': {e}")
                
                # Crear respuesta amigable
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Error de compatibilidad con servicio externo",
                        "message": "El servicio está temporalmente no disponible",
                        "code": "GRADIO_BOOL_ERROR",
                        "type": "compatibility_error"
                    }
                )
            
            # Si es otro error de tipo, re-lanzarlo
            raise
