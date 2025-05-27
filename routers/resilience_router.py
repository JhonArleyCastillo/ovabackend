"""
Router para monitoreo de patrones de resiliencia.
Proporciona endpoints para verificar el estado de los servicios y circuit breakers.
"""
from fastapi import APIRouter, HTTPException
from backend.services.resilience_service import ResilienceService
from backend.services.huggingface_service import verify_hf_connection_async
import logging
import asyncio

logger = logging.getLogger(__name__)

resilience_router = APIRouter(prefix="/resilience", tags=["resilience"])

@resilience_router.get("/health")
async def health_check():
    """Endpoint de health check que verifica todos los servicios críticos."""
    try:
        # Verificar conexión con Hugging Face usando resiliencia
        hf_status = await verify_hf_connection_async()
        
        return {
            "status": "healthy" if hf_status else "degraded",
            "services": {
                "huggingface": "up" if hf_status else "down"
            },
            "circuit_breakers": ResilienceService.get_circuit_breaker_status()
        }
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@resilience_router.get("/status")
async def resilience_status():
    """Endpoint que retorna el estado de los patrones de resiliencia."""
    try:
        return {
            "resilience_patterns": {
                "circuit_breaker": "enabled",
                "retry": "enabled", 
                "timeout": "enabled",
                "fallback": "enabled"
            },
            "circuit_breakers": ResilienceService.get_circuit_breaker_status()
        }
    except Exception as e:
        logger.error(f"Error obteniendo estado de resiliencia: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@resilience_router.post("/test-resilience")
async def test_resilience():
    """Endpoint para probar los patrones de resiliencia con una llamada controlada."""
    try:
        # Hacer una llamada de prueba que use los patrones de resiliencia
        test_result = await verify_hf_connection_async()
        
        return {
            "test_status": "success" if test_result else "failed",
            "message": "Resilience patterns working correctly" if test_result else "Service degraded but resilience active"
        }
    except Exception as e:
        logger.error(f"Error en test de resiliencia: {e}")
        return {
            "test_status": "error",
            "message": f"Resilience test failed: {str(e)}"
        }

@resilience_router.post("/reset-circuit-breaker")
async def reset_circuit_breaker():
    """Endpoint para resetear el circuit breaker manualmente."""
    try:
        ResilienceService.reset_circuit_breaker()
        return {
            "status": "success",
            "message": "Circuit breaker reseteado exitosamente",
            "circuit_breaker_status": ResilienceService.get_circuit_breaker_status()
        }
    except Exception as e:
        logger.error(f"Error reseteando circuit breaker: {e}")
        raise HTTPException(status_code=500, detail="Error resetting circuit breaker")
