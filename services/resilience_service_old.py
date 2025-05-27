"""
Servicio de resiliencia usando Hyx para manejar múltiples caídas consecutivas.
Implementa Circuit Breaker, Retry, Timeout y Fallback para servicios externos.
"""
import asyncio
from typing import Callable, Any, Optional
import logging
from functools import wraps
import time

# Importaciones correctas de Hyx basadas en la API real
from hyx.retry.api import retry
from hyx.retry.backoffs import expo
from hyx.retry.counters import count

logger = logging.getLogger(__name__)


class ResilienceService:
    """Servicio centralizado para patrones de resiliencia."""
    
    # Configuraciones por defecto optimizadas para servicios de IA
    DEFAULT_RETRY_CONFIG = {
        "attempts": 3,
        "backoff": expo(base=1, max_time=10),  # Backoff exponencial
        "exceptions": (ConnectionError, TimeoutError, OSError, Exception)
    }
    
    # Simulación simple de circuit breaker (ya que Hyx 0.0.2 es básico)
    _circuit_breaker_state = {
        "failure_count": 0,
        "last_failure_time": None,
        "is_open": False,
        "failure_threshold": 5,
        "recovery_timeout": 30
    }

    @staticmethod
    def resilient_hf_call(
        timeout_seconds: float = 30.0,
        retry_attempts: int = 3,
        fallback_response: Optional[str] = None
    ):
        """
        Decorador que aplica patrones de resiliencia a llamadas de Hugging Face.
        
        Args:
            timeout_seconds: Tiempo límite para la operación
            retry_attempts: Número de intentos
            fallback_response: Respuesta por defecto si falla todo
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Configurar timeout
                timeout_policy = TimeoutPolicy(timeout=timeout_seconds)
                
                # Configurar retry con backoff exponencial
                retry_policy = RetryPolicy(
                    attempts=retry_attempts,
                    backoff_strategy=ExponentialBackoffStrategy(
                        initial_delay=1.0,
                        max_delay=10.0,
                        multiplier=2.0
                    ),
                    exceptions=(ConnectionError, TimeoutError, OSError, Exception)
                )
                
                # Configurar circuit breaker
                cb_policy = CircuitBreakerPolicy(
                    failure_threshold=5,
                    recovery_timeout=30,
                    expected_exception=(ConnectionError, TimeoutError, OSError, Exception)
                )
                
                # Función con fallback
                async def resilient_func():
                    try:
                        # Aplicar timeout -> retry -> circuit breaker
                        @timeout(timeout_policy)
                        @retry(retry_policy)
                        @circuit_breaker(cb_policy)
                        async def protected_call():
                            if asyncio.iscoroutinefunction(func):
                                return await func(*args, **kwargs)
                            else:
                                # Para funciones síncronas, ejecutar en thread pool
                                return await asyncio.get_event_loop().run_in_executor(
                                    None, func, *args, **kwargs
                                )
                        
                        return await protected_call()
                    except Exception as e:
                        logger.error(f"Todos los patrones de resiliencia fallaron: {e}")
                        if fallback_response is not None:
                            logger.info(f"Usando respuesta de fallback: {fallback_response}")
                            return fallback_response
                        raise
                
                return await resilient_func()
            
            return wrapper
        return decorator

    @staticmethod
    def simple_retry(attempts: int = 3, delay: float = 1.0):
        """
        Decorador simple de retry para funciones que no requieren circuit breaker.
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                retry_policy = RetryPolicy(
                    attempts=attempts,
                    backoff_strategy=ExponentialBackoffStrategy(
                        initial_delay=delay,
                        max_delay=delay * 4,
                        multiplier=2.0
                    ),
                    exceptions=(ConnectionError, TimeoutError, OSError, Exception)
                )
                
                @retry(retry_policy)
                async def protected_call():
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return await asyncio.get_event_loop().run_in_executor(
                            None, func, *args, **kwargs
                        )
                
                return await protected_call()
            
            return wrapper
        return decorator

    @staticmethod
    def get_circuit_breaker_status() -> dict:
        """Retorna el estado actual de los circuit breakers (para monitoring)."""
        # En versiones futuras de Hyx esto podría estar disponible
        return {"status": "monitoring_not_implemented"}


# Instancia global del servicio
resilience_service = ResilienceService()
