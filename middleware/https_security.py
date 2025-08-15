"""
Middleware de seguridad HTTPS para FastAPI

Este middleware garantiza que en producción:
- Solo se acepten conexiones HTTPS
- Se apliquen headers de seguridad
- Se rechacen requests HTTP inseguros
"""

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
import logging
from config import IS_DEVELOPMENT, FORCE_HTTPS, SECURITY_HEADERS

logger = logging.getLogger(__name__)

async def https_security_middleware(request: Request, call_next):
    """
    Middleware que fuerza HTTPS y aplica headers de seguridad en producción.
    
    En desarrollo permite HTTP para localhost.
    En producción rechaza cualquier request HTTP.
    """
    
    # En desarrollo, permitir todo
    if IS_DEVELOPMENT:
        response = await call_next(request)
        return response
    
    # En producción, validar seguridad
    if FORCE_HTTPS:
        # Verificar protocolo
        scheme = request.url.scheme
        if scheme != "https":
            # Rechazar HTTP en producción
            logger.warning(f"🚨 Request HTTP rechazado en producción: {request.url}")
            raise HTTPException(
                status_code=426,
                detail="Upgrade Required: Solo HTTPS está permitido en producción"
            )
        
        # Verificar headers de proxy (para deploys detrás de load balancers)
        forwarded_proto = request.headers.get("X-Forwarded-Proto")
        if forwarded_proto and forwarded_proto.lower() != "https":
            logger.warning(f"🚨 Request con X-Forwarded-Proto inseguro: {forwarded_proto}")
            raise HTTPException(
                status_code=426,
                detail="Upgrade Required: Solo HTTPS está permitido"
            )
    
    # Procesar request
    response = await call_next(request)
    
    # Aplicar headers de seguridad en producción
    if not IS_DEVELOPMENT:
        for header_name, header_value in SECURITY_HEADERS.items():
            response.headers[header_name] = header_value
        
        # Header adicional para indicar que el server requiere HTTPS
        response.headers["X-HTTPS-Required"] = "true"
    
    return response

def validate_cors_origin(origin: str) -> bool:
    """
    Valida que el origin sea seguro en producción.
    
    Args:
        origin: El origin del request
        
    Returns:
        bool: True si el origin es válido
    """
    if IS_DEVELOPMENT:
        return True
    
    if not origin:
        return False
    
    # En producción, solo HTTPS
    if not origin.startswith("https://"):
        logger.warning(f"🚨 Origin HTTP rechazado en producción: {origin}")
        return False
    
    # No permitir localhost en producción
    if "localhost" in origin.lower() or "127.0.0.1" in origin:
        logger.warning(f"🚨 Origin localhost rechazado en producción: {origin}")
        return False
    
    return True
