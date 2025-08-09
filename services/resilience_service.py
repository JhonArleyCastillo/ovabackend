"""
Resilience service for handling multiple consecutive failures.

Implements resilience patterns including retry with exponential backoff and
circuit breaker simulation for external service calls. Pure-Python implementation
without external dependencies.
"""

import asyncio
from typing import Callable, Any, Optional, Dict, Union
import logging
from functools import wraps
import time

# Configure module logger
logger = logging.getLogger(__name__)

def _compute_backoff_delay(attempt: int, *, min_delay: float, base: float, max_delay: float) -> float:
    """Compute exponential backoff delay with clamping."""
    delay = min_delay * (base ** (attempt - 1))
    return delay if delay < max_delay else max_delay


class ResilienceService:
    """
    Centralized service for implementing resilience patterns.
    
    Provides circuit breaker simulation, retry mechanisms, and
    failure tracking for external service calls.
    """
    
    # Circuit breaker state simulation
    _circuit_breaker_state: Dict[str, Union[int, float, bool]] = {
        "failure_count": 0,
        "last_failure_time": None,
        "is_open": False,
        "failure_threshold": 5,
        "recovery_timeout": 30
    }

    @classmethod
    def _check_circuit_breaker(cls) -> bool:
        """
        Check the current state of the simulated circuit breaker.
        
        Returns:
            bool: True if circuit is closed (allowing calls), 
                  False if open (blocking calls).
        """
        current_time = time.time()
        
        # If circuit breaker is open, check if recovery should be attempted
        if cls._circuit_breaker_state["is_open"]:
            last_failure = cls._circuit_breaker_state["last_failure_time"]
            recovery_timeout = cls._circuit_breaker_state["recovery_timeout"]
            
            if (current_time - last_failure) >= recovery_timeout:
                logger.info("Circuit breaker: Attempting recovery")
                cls._circuit_breaker_state["is_open"] = False
                cls._circuit_breaker_state["failure_count"] = 0
                return True
            else:
                logger.warning("Circuit breaker is open, rejecting call")
                return False
        
        return True

    @classmethod
    def _record_success(cls) -> None:
        """
        Record a successful operation in the circuit breaker.
        
        Resets failure count and ensures circuit remains closed.
        """
        """Registra un éxito en el circuit breaker."""
        cls._circuit_breaker_state["failure_count"] = 0
        cls._circuit_breaker_state["is_open"] = False

    @classmethod
    def _record_failure(cls):
        """Registra un fallo en el circuit breaker."""
        cls._circuit_breaker_state["failure_count"] += 1
        cls._circuit_breaker_state["last_failure_time"] = time.time()
        
        if cls._circuit_breaker_state["failure_count"] >= cls._circuit_breaker_state["failure_threshold"]:
            cls._circuit_breaker_state["is_open"] = True
            logger.error("Circuit breaker abierto debido a múltiples fallos")

    @staticmethod
    def resilient_hf_call(
        timeout_seconds: float = 30.0,
        retry_attempts: int = 3,
        fallback_response: Optional[Any] = None
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
                # Verificar circuit breaker antes de intentar
                if not ResilienceService._check_circuit_breaker():
                    if fallback_response is not None:
                        logger.info(f"Circuit breaker abierto, usando fallback: {fallback_response}")
                        return fallback_response
                    raise ConnectionError("Circuit breaker está abierto")

                # Parámetros de backoff
                min_delay = 1.0
                base = 2.0
                max_delay = 10.0

                last_exception: Optional[Exception] = None
                for attempt in range(1, max(1, retry_attempts) + 1):
                    try:
                        # Implementar timeout manualmente
                        if asyncio.iscoroutinefunction(func):
                            result = await asyncio.wait_for(
                                func(*args, **kwargs),
                                timeout=timeout_seconds
                            )
                        else:
                            # Para funciones síncronas
                            result = await asyncio.wait_for(
                                asyncio.get_event_loop().run_in_executor(
                                    None, func, *args, **kwargs
                                ),
                                timeout=timeout_seconds
                            )

                        # Registrar éxito en circuit breaker
                        ResilienceService._record_success()
                        return result

                    except asyncio.TimeoutError:
                        last_exception = TimeoutError(f"Operación excedió {timeout_seconds} segundos")
                        logger.error(f"[Intento {attempt}/{retry_attempts}] Timeout después de {timeout_seconds} segundos")
                        ResilienceService._record_failure()
                    except (ConnectionError, OSError) as e:
                        last_exception = e
                        logger.error(f"[Intento {attempt}/{retry_attempts}] Error de conexión/E/S: {e}")
                        ResilienceService._record_failure()
                    except Exception as e:
                        last_exception = e
                        logger.error(f"[Intento {attempt}/{retry_attempts}] Error en llamada resiliente: {e}")
                        ResilienceService._record_failure()

                    # Si quedan intentos, esperar con backoff
                    if attempt < max(1, retry_attempts):
                        delay = _compute_backoff_delay(attempt, min_delay=min_delay, base=base, max_delay=max_delay)
                        await asyncio.sleep(delay)

                logger.error(f"Todos los patrones de resiliencia fallaron: {last_exception}")
                if fallback_response is not None:
                    logger.info(f"Usando respuesta de fallback: {fallback_response}")
                    return fallback_response
                raise last_exception if last_exception else RuntimeError("Llamada resiliente fallida")
            
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
                max_attempts = max(1, attempts)
                base = 2.0
                max_delay = delay * 8 if delay > 0 else 1.0
                last_exception: Optional[Exception] = None

                for attempt in range(1, max_attempts + 1):
                    try:
                        if asyncio.iscoroutinefunction(func):
                            return await func(*args, **kwargs)
                        else:
                            loop = asyncio.get_event_loop()
                            return await loop.run_in_executor(None, func, *args, **kwargs)
                    except (ConnectionError, TimeoutError, OSError, Exception) as e:
                        last_exception = e
                        if attempt < max_attempts:
                            sleep_for = _compute_backoff_delay(attempt, min_delay=max(0.0, delay), base=base, max_delay=max_delay)
                            await asyncio.sleep(sleep_for)
                        else:
                            raise
            
            return wrapper
        return decorator
    
    @staticmethod
    def reset_circuit_breaker():
        """Resetea el circuit breaker manualmente."""
        ResilienceService._circuit_breaker_state["failure_count"] = 0
        ResilienceService._circuit_breaker_state["is_open"] = False
        ResilienceService._circuit_breaker_state["last_failure_time"] = None
        logger.info("Circuit breaker reseteado manualmente")

    @staticmethod
    def get_retry_stats(service_name: str = "default") -> dict:
        """Retorna estadísticas de retry para un servicio específico."""
        # Por simplicidad, retornamos estadísticas básicas
        # En una implementación real, esto sería más sofisticado
        return {
            "service_name": service_name,
            "total_retries": 0,
            "successful_retries": 0,
            "failed_retries": 0,
            "last_retry_time": None
        }

    @staticmethod 
    def get_circuit_breaker_status(service_name: str = "default") -> dict:
        """Retorna el estado actual del circuit breaker para un servicio específico."""
        # Por simplicidad, usamos el estado global
        # En una implementación real, cada servicio tendría su propio estado
        return {
            "service_name": service_name,
            "is_open": ResilienceService._circuit_breaker_state["is_open"],
            "failure_count": ResilienceService._circuit_breaker_state["failure_count"],
            "failure_threshold": ResilienceService._circuit_breaker_state["failure_threshold"],
            "last_failure_time": ResilienceService._circuit_breaker_state["last_failure_time"],
            "recovery_timeout": ResilienceService._circuit_breaker_state["recovery_timeout"]
        }
