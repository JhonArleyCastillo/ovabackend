"""
Cliente Gradio Robusto con manejo de excepciones y compatibilidad mejorada

Este módulo proporciona una capa de abstracción sobre gradio_client
para manejar errores comunes como 'bool is not iterable' y ofrece
múltiples estrategias de inicialización y predicción.
"""

import os
import time
import logging
import tempfile
import json
import requests
from typing import Dict, Any, Optional, List, Tuple, Union, Callable
from urllib.parse import urljoin, urlparse
import base64
import io
from PIL import Image

# Imports condicionales para no romper en entornos sin dependencias
try:
    from gradio_client import Client, handle_file
    from gradio_client.serializing import stringify_file
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False

# Configuración de logger
logger = logging.getLogger(__name__)

class GradioRobustClient:
    """
    Cliente Gradio robusto con manejo especial para errores comunes
    como 'bool is not iterable' y diversas estrategias de inicialización.
    
    Características:
    - Múltiples estrategias de inicialización del cliente
    - Manejo específico del error 'bool is not iterable'
    - Fallback a requests directas si gradio_client falla
    - Timeouts y reintentos configurables
    - Validación de respuestas y parseo inteligente
    """
    
    def __init__(self, 
                 space_url: str, 
                 hf_token: Optional[str] = None,
                 correlation_id: Optional[str] = None,
                 timeout: float = 60.0,
                 max_retries: int = 3):
        """
        Inicializa un cliente robusto para Gradio.
        
        Args:
            space_url: URL del Gradio Space
            hf_token: Token de Hugging Face (opcional)
            correlation_id: ID para tracking (opcional)
            timeout: Timeout en segundos para requests
            max_retries: Número máximo de reintentos
        """
        self.space_url = space_url
        self.hf_token = hf_token
        self.correlation_id = correlation_id or f"gc_{int(time.time())}"
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = None
        
        # Guardar información de healthcheck
        self._config = None
        self._api_info = None
        
        # Inicializar cliente con estrategias múltiples
        self._initialize_client()
    
    def _initialize_client(self) -> bool:
        """
        Intenta inicializar el cliente Gradio con múltiples estrategias.
        
        Returns:
            bool: True si se pudo crear el cliente, False en caso contrario
        """
        if not GRADIO_AVAILABLE:
            logger.error(f"[{self.correlation_id}] ❌ gradio_client no está instalado")
            return False
        
        # Estrategias de inicialización del cliente
        strategies = [
            {
                "name": "standard",
                "method": self._init_standard_client,
                "args": {"hf_token": self.hf_token} if self.hf_token else {}
            },
            {
                "name": "no_token",
                "method": self._init_standard_client,
                "args": {}  # Sin token, por si el token causa problemas
            },
            {
                "name": "with_session",
                "method": self._init_session_client,
                "args": {"hf_token": self.hf_token} if self.hf_token else {}
            },
            {
                "name": "direct_requests",
                "method": self._init_request_fallback,
                "args": {}
            }
        ]
        
        # Intentar cada estrategia
        for strategy in strategies:
            try:
                name = strategy["name"]
                method = strategy["method"]
                args = strategy["args"]
                
                logger.debug(f"[{self.correlation_id}] 🔄 Intentando inicialización con estrategia: {name}")
                success = method(**args)
                
                if success:
                    logger.info(f"[{self.correlation_id}] ✅ Cliente inicializado con estrategia: {name}")
                    return True
                
            except Exception as e:
                error_msg = str(e).lower()
                if "bool" in error_msg and "iterable" in error_msg:
                    logger.warning(f"[{self.correlation_id}] ⚠️ Error de iteración booleana en estrategia {name}: {e}")
                else:
                    logger.warning(f"[{self.correlation_id}] ⚠️ Error en estrategia {name}: {e}")
        
        # Si llegamos aquí, todas las estrategias fallaron
        logger.error(f"[{self.correlation_id}] ❌ Todas las estrategias de inicialización fallaron")
        return False
    
    def _init_standard_client(self, **kwargs) -> bool:
        """Inicialización estándar del cliente Gradio."""
        try:
            # La forma estándar, pero con manejo de errores especial
            self.client = Client(self.space_url, **kwargs)
            
            # Verificar que el cliente se creó correctamente
            if hasattr(self.client, "predict") and callable(self.client.predict):
                return True
            return False
            
        except Exception as e:
            # Manejar específicamente el error bool
            error_msg = str(e).lower()
            if "bool" in error_msg and "iterable" in error_msg:
                logger.warning(f"[{self.correlation_id}] ⚠️ Error de tipo bool en inicialización: {e}")
            else:
                logger.warning(f"[{self.correlation_id}] ⚠️ Error en inicialización estándar: {e}")
            return False
    
    def _init_session_client(self, **kwargs) -> bool:
        """Inicialización con sesión personalizada."""
        try:
            # Algunas versiones de gradio_client tienen problemas con el manejo de sesión
            # Crear una sesión limpia puede ayudar
            import requests
            session = requests.Session()
            
            # Añadir token si está disponible
            if self.hf_token and "hf_token" in kwargs:
                session.headers.update({"Authorization": f"Bearer {self.hf_token}"})
            
            # Algunos clientes de Gradio aceptan una sesión directamente
            try:
                self.client = Client(self.space_url, session=session)
                return True
            except:
                # Si no acepta session como parámetro, intentamos con el cliente estándar
                return self._init_standard_client(**kwargs)
                
        except Exception as e:
            logger.warning(f"[{self.correlation_id}] ⚠️ Error en inicialización con sesión: {e}")
            return False
    
    def _init_request_fallback(self, **kwargs) -> bool:
        """
        Fallback usando requests directamente si gradio_client falla.
        
        Esta es una implementación parcial que permite comunicarse
        directamente con la API de Gradio sin usar el cliente oficial.
        """
        try:
            # Verificar que podemos acceder al espacio
            headers = {}
            if self.hf_token:
                headers["Authorization"] = f"Bearer {self.hf_token}"
            
            # Probar conexión a config
            config_url = urljoin(self.space_url, "config")
            response = requests.get(config_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                self._config = response.json()
                
                # Intentar obtener info de la API
                api_info_url = urljoin(self.space_url, "gradio_api/info")
                info_response = requests.get(api_info_url, headers=headers, timeout=10)
                
                if info_response.status_code == 200:
                    try:
                        # serialize=False puede causar problemas en algunos endpoints
                        self._api_info = info_response.json()
                    except:
                        logger.debug(f"[{self.correlation_id}] ⚠️ No se pudo parsear info API como JSON")
                
                # Cliente simulado para usar con fallback de requests
                self.client = "REQUESTS_FALLBACK"
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"[{self.correlation_id}] ⚠️ Error en fallback de requests: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Realiza un health check del espacio de Gradio.
        
        Returns:
            Dict con estado y detalles
        """
        status = {
            "url": self.space_url,
            "is_available": False,
            "client_type": "unknown",
            "error": None
        }
        
        # Verificar si tenemos cliente
        if not self.client:
            status["error"] = "No se pudo inicializar el cliente"
            return status
        
        # Identificar tipo de cliente
        if self.client == "REQUESTS_FALLBACK":
            status["client_type"] = "requests_fallback"
            status["is_available"] = True if self._config else False
        else:
            status["client_type"] = "gradio_client"
            try:
                # Intentar acceder al cliente para ver si está activo
                if hasattr(self.client, "predict") and callable(self.client.predict):
                    status["is_available"] = True
            except Exception as e:
                status["error"] = str(e)
        
        return status
    
    def predict(self, 
                image_path: str, 
                api_name: Optional[str] = None,
                timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Realiza una predicción robusta con múltiples estrategias.
        
        Args:
            image_path: Ruta a la imagen para la predicción
            api_name: Nombre de la API a usar (opcional)
            timeout: Tiempo límite en segundos (opcional)
            
        Returns:
            Dict con resultados o error
        """
        if not self.client:
            return self._error_response("Cliente no inicializado")
        
        # Usar timeout del objeto o el parámetro
        timeout = timeout or self.timeout
        
        # Verificar que la imagen existe
        if not os.path.exists(image_path):
            return self._error_response(f"Imagen no encontrada: {image_path}")
        
        # Estrategia según tipo de cliente
        if self.client == "REQUESTS_FALLBACK":
            return self._predict_with_requests(image_path, api_name, timeout)
        else:
            return self._predict_with_gradio(image_path, api_name, timeout)
    
    def _predict_with_gradio(self, 
                            image_path: str, 
                            api_name: Optional[str] = None,
                            timeout: float = 60.0) -> Dict[str, Any]:
        """Predicción usando el cliente Gradio oficial."""
        # Lista de API names a probar si no se especifica uno
        api_names_to_try = [api_name] if api_name else ["/predict", "/process", "/classify", None]
        
        # Estrategias de llamada a la API para máxima compatibilidad
        strategies = [
            {
                "name": "posicional",
                "params": lambda: [handle_file(image_path)]
            },
            {
                "name": "nombrado",
                "params": lambda: {"image": handle_file(image_path)}
            },
            {
                "name": "file_path",
                "params": lambda: [image_path]
            },
            {
                "name": "binary",
                "params": lambda: [open(image_path, "rb")]
            }
        ]
        
        # Intentar cada combinación de API y estrategia
        for api in api_names_to_try:
            for strategy in strategies:
                try:
                    strategy_name = strategy["name"]
                    params_func = strategy["params"]
                    
                    logger.debug(f"[{self.correlation_id}] 🔄 Probando {strategy_name} con API: {api or 'default'}")
                    
                    # Obtener parámetros para esta estrategia
                    params = params_func()
                    
                    # Llamar a la API según el tipo de parámetros
                    if isinstance(params, dict):
                        if api:
                            result = self.client.predict(**params, api_name=api)
                        else:
                            result = self.client.predict(**params)
                    else:
                        if api:
                            result = self.client.predict(*params, api_name=api)
                        else:
                            result = self.client.predict(*params)
                    
                    # Parsear resultado
                    parsed = self._parse_result(result)
                    if parsed:
                        logger.info(f"[{self.correlation_id}] ✅ Predicción exitosa con {strategy_name}:{api or 'default'}")
                        return parsed
                
                except Exception as e:
                    error_msg = str(e).lower()
                    if "bool" in error_msg and "iterable" in error_msg:
                        logger.debug(f"[{self.correlation_id}] ⚠️ Error bool en {strategy_name}:{api or 'default'} - {e}")
                    else:
                        logger.debug(f"[{self.correlation_id}] ⚠️ Error en {strategy_name}:{api or 'default'} - {e}")
        
        # Si todas las estrategias fallaron
        return self._error_response("Todas las estrategias de predicción fallaron")
    
    def _predict_with_requests(self,
                              image_path: str,
                              api_name: Optional[str] = None,
                              timeout: float = 60.0) -> Dict[str, Any]:
        """Predicción usando requests directamente como fallback."""
        if not self._config:
            return self._error_response("No se pudo obtener configuración del espacio")
        
        try:
            # Configurar headers
            headers = {}
            if self.hf_token:
                headers["Authorization"] = f"Bearer {self.hf_token}"
            
            # Determinar endpoint a usar
            endpoint = api_name or "/predict"
            if not endpoint.startswith("/"):
                endpoint = f"/{endpoint}"
            
            api_url = urljoin(self.space_url, f"run{endpoint}")
            
            # Preparar la imagen
            with open(image_path, "rb") as f:
                # Codificar imagen para enviar por API
                image_bytes = f.read()
                image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            
            # Datos para la solicitud
            data = {
                "data": [
                    # La mayoría de Gradio Spaces esperan un único parámetro que es la imagen
                    image_b64
                ]
            }
            
            # Realizar la solicitud
            response = requests.post(
                api_url,
                headers=headers,
                json=data,
                timeout=timeout
            )
            
            # Verificar respuesta
            if response.status_code == 200:
                try:
                    result = response.json()
                    # La respuesta de Gradio suele tener un campo 'data'
                    if "data" in result and isinstance(result["data"], list) and len(result["data"]) > 0:
                        return self._parse_result(result["data"])
                    else:
                        return self._parse_result(result)
                except Exception as e:
                    return self._error_response(f"Error al parsear respuesta: {e}")
            else:
                return self._error_response(f"Error HTTP {response.status_code}: {response.text[:100]}...")
            
        except Exception as e:
            return self._error_response(f"Error en predicción con requests: {e}")
    
    def _parse_result(self, result: Any) -> Dict[str, Any]:
        """
        Parsea el resultado de Gradio a un formato estandarizado.
        
        Args:
            result: Resultado de la predicción
            
        Returns:
            Dict con resultado parseado
        """
        try:
            # Caso 1: Lista con [label, confidence, ...]
            if isinstance(result, (list, tuple)) and len(result) >= 2:
                if isinstance(result[0], str) and isinstance(result[1], (int, float)):
                    label = result[0]
                    confidence = float(result[1])
                    
                    # Normalizar confianza a porcentaje
                    if confidence <= 1.0:
                        confidence *= 100
                    
                    return {
                        "resultado": label,
                        "confianza": round(confidence, 2),
                        "alternativas": [],
                        "source": "gradio_list"
                    }
            
            # Caso 2: Diccionario directo
            if isinstance(result, dict):
                label = result.get('label', result.get('prediction', result.get('result', 'Desconocido')))
                confidence = result.get('confidence', result.get('score', result.get('probability', 0.0)))
                
                if isinstance(confidence, (int, float)):
                    confidence = float(confidence)
                    if confidence <= 1.0:
                        confidence *= 100
                else:
                    confidence = 0.0
                
                return {
                    "resultado": str(label),
                    "confianza": round(confidence, 2),
                    "alternativas": [],
                    "source": "gradio_dict"
                }
            
            # Caso 3: String (formato legacy)
            if isinstance(result, str):
                import re
                # Buscar patrón "label (confidence%)"
                pattern = r"(.*)\s*\((\d+\.?\d*)%?\)"
                match = re.search(pattern, result)
                
                if match:
                    label = match.group(1).strip()
                    confidence = float(match.group(2))
                    return {
                        "resultado": label,
                        "confianza": round(confidence, 2),
                        "alternativas": [],
                        "source": "gradio_string_pattern"
                    }
                else:
                    # Si no hay patrón, es solo un string de resultado
                    return {
                        "resultado": result,
                        "confianza": 80.0,  # Confianza predeterminada
                        "alternativas": [],
                        "source": "gradio_string"
                    }
            
            # Caso 4: Valor simple (número, bool)
            if isinstance(result, (int, float, bool)):
                return {
                    "resultado": str(result),
                    "confianza": 100.0,
                    "alternativas": [],
                    "source": "gradio_simple_value"
                }
            
            # Caso 5: Otro tipo de objeto (fallback genérico)
            return {
                "resultado": str(result),
                "confianza": 50.0,
                "alternativas": [],
                "source": "gradio_unknown"
            }
            
        except Exception as e:
            return self._error_response(f"Error al parsear resultado: {e}")
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """
        Crea un objeto de respuesta de error estandarizado.
        
        Args:
            message: Mensaje de error
            
        Returns:
            Dict con estructura de error
        """
        logger.error(f"[{self.correlation_id}] ❌ {message}")
        return {
            "resultado": "Error",
            "confianza": 0.0,
            "alternativas": [],
            "source": "error",
            "error": message
        }
