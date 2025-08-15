"""
Servicio robusto de Gradio con manejo de incompatibilidades local/producción.

Este módulo soluciona las diferencias entre entornos:
- Local: Spaces públicos sin autenticación
- Producción: Spaces privados con tokens HF
- Fallbacks automáticos cuando un servicio falla
- Configuración dual según entorno

Uso: GradioCompatibilityService.get_asl_prediction(image)
"""

import os
import logging
import time
import tempfile
import json
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image
import numpy as np

try:
    from config import HF_TOKEN  # Uso centralizado del token
except Exception:
    HF_TOKEN = os.getenv('HF_TOKEN')

try:
    from gradio_client import Client, handle_file
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False
    
try:
    from huggingface_hub import login
    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False

logger = logging.getLogger(__name__)

class GradioCompatibilityService:
    """
    Servicio que maneja las incompatibilidades de Gradio entre entornos.
    
    Estrategia de fallback:
    1. Gradio Space primario (configurado en environment)
    2. Gradio Space público de fallback
    3. Respuesta de error estructurada
    """
    
    def __init__(self):
        self.environment = os.getenv('ENVIRONMENT', 'local')
        self.is_production = self.environment.lower() == 'production'
        # Configuración según entorno
        self.primary_space_url = os.getenv('HF_ASL_SPACE_URL', 'https://jhonarleycastillov-asl-image.hf.space')
        # Token viene preferentemente de config central
        self.hf_token = HF_TOKEN or os.getenv('HF_TOKEN')
        # Spaces de fallback públicos (no requieren autenticación)
        self.fallback_spaces = [
            'https://amd-gpt-oss-120b-chatbot.hf.space',  # Ejemplo público
            # Agregar más spaces públicos ASL aquí
        ]
        # Configuraciones específicas por entorno
        if self.is_production:
            logger.info("🏭 Modo PRODUCCIÓN - usando configuración con autenticación")
            if not self.hf_token:
                logger.warning("⚠️ HF_TOKEN no configurado en producción - limitaciones esperadas")
        else:
            logger.info("🛠️ Modo LOCAL/DESARROLLO - usando configuración simple")
    
    def _create_gradio_client(self, space_url: str, with_auth: bool = True) -> Optional[Client]:
        """
        Crea cliente Gradio con configuración apropiada según entorno.
        
        Args:
            space_url: URL del Gradio Space
            with_auth: Si debe usar autenticación (False para spaces públicos)
        """
        try:
            if not GRADIO_AVAILABLE:
                logger.error("❌ gradio_client no está disponible")
                return None
            
            client_kwargs = {}
            
            # En producción, intentar con autenticación si está disponible
            if self.is_production and with_auth and self.hf_token:
                client_kwargs['hf_token'] = self.hf_token
                logger.debug(f"🔐 Creando cliente autenticado para {space_url}")
            else:
                logger.debug(f"🔓 Creando cliente sin autenticación para {space_url}")
            
            client = Client(space_url, **client_kwargs)
            return client
            
        except Exception as e:
            logger.error(f"❌ Error creando cliente Gradio para {space_url}: {e}")
            return None
    
    def _try_gradio_prediction(self, client: Client, image_path: str, correlation_id: str) -> Optional[Dict[str, Any]]:
        """
        Intenta predicción con un cliente Gradio específico.
        
        Args:
            client: Cliente Gradio configurado
            image_path: Ruta al archivo de imagen temporal
            correlation_id: ID para tracking
            
        Returns:
            Resultado estructurado o None si falla
        """
        try:
            prefix = f"[ASL_GRADIO][{correlation_id}]"
            
            # Intentar diferentes API names comunes
            api_names = ["/predict", "/process", "/classify", "/api_name"]
            
            result = None
            for api_name in api_names:
                try:
                    logger.debug(f"{prefix} Probando API name: {api_name}")
                    start_time = time.time()
                    
                    result = client.predict(
                        image=handle_file(image_path),
                        api_name=api_name
                    )
                    
                    call_ms = (time.time() - start_time) * 1000
                    logger.info(f"{prefix} ✅ Éxito con {api_name} en {call_ms:.1f}ms")
                    break
                    
                except Exception as api_error:
                    logger.debug(f"{prefix} ❌ Fallo {api_name}: {api_error}")
                    continue
            
            if result is None:
                logger.error(f"{prefix} ❌ Todos los API names fallaron")
                return None
            
            # Procesar resultado
            return self._parse_gradio_result(result, correlation_id)
            
        except Exception as e:
            logger.error(f"❌ Error en predicción Gradio: {e}")
            return None
    
    def _parse_gradio_result(self, result: Any, correlation_id: str) -> Dict[str, Any]:
        """
        Parsea el resultado de Gradio a formato estándar.
        
        Maneja múltiples formatos que pueden venir de diferentes Spaces.
        """
        prefix = f"[PARSER][{correlation_id}]"
        
        try:
            # Log para debugging
            result_type = type(result).__name__
            logger.debug(f"{prefix} Parseando resultado tipo: {result_type}")
            
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
                label = result.get('label', result.get('prediction', 'Desconocido'))
                confidence = result.get('confidence', result.get('score', 0.0))
                
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
                match = re.search(r'([A-Za-z0-9]+)\s*\((\d+(?:\.\d+)?)%?\)', result)
                if match:
                    label = match.group(1)
                    confidence = float(match.group(2))
                    
                    return {
                        "resultado": label,
                        "confianza": round(confidence, 2),
                        "alternativas": [],
                        "source": "gradio_string"
                    }
                
                # Si no hay patrón, usar el string completo
                return {
                    "resultado": result.strip(),
                    "confianza": 0.0,
                    "alternativas": [],
                    "source": "gradio_raw_string"
                }
            
            # Caso por defecto: formato no reconocido
            logger.warning(f"{prefix} Formato no reconocido: {result_type}")
            return {
                "resultado": str(result),
                "confianza": 0.0,
                "alternativas": [],
                "source": "gradio_unknown"
            }
            
        except Exception as e:
            logger.error(f"{prefix} Error parseando resultado: {e}")
            return {
                "resultado": "Error de parsing",
                "confianza": 0.0,
                "alternativas": [],
                "source": "gradio_error"
            }
    
    # Eliminado: Fallback vía Inference API de modelos directos. Política actual: solo Spaces.
    
    def get_asl_prediction(self, image: Image.Image, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene predicción ASL usando estrategia de fallback robusta.
        
        Args:
            image: Imagen PIL a procesar
            correlation_id: ID para tracking (opcional)
            
        Returns:
            Diccionario con resultado estructurado
        """
        if correlation_id is None:
            correlation_id = f"asl_{int(time.time())}"
        
        prefix = f"[ASL_COMPAT][{correlation_id}]"
        logger.info(f"{prefix} 🚀 Iniciando predicción ASL robusta")
        
        # Preparar imagen temporal para Gradio
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                image.convert("RGB").save(tmp_file.name, format='PNG')
                temp_path = tmp_file.name
            
            # Estrategia 1: Space primario
            logger.info(f"{prefix} 📡 Estrategia 1: Space primario ({self.primary_space_url})")
            client = self._create_gradio_client(self.primary_space_url, with_auth=True)
            if client:
                result = self._try_gradio_prediction(client, temp_path, correlation_id)
                if result and result.get('confianza', 0) > 0:
                    logger.info(f"{prefix} ✅ Éxito con space primario")
                    return result
            
            # Estrategia 2: Spaces de fallback públicos
            logger.info(f"{prefix} 📡 Estrategia 2: Spaces de fallback públicos")
            for fallback_url in self.fallback_spaces:
                client = self._create_gradio_client(fallback_url, with_auth=False)
                if client:
                    result = self._try_gradio_prediction(client, temp_path, correlation_id)
                    if result and result.get('confianza', 0) > 0:
                        logger.info(f"{prefix} ✅ Éxito con fallback: {fallback_url}")
                        return result
            
            # Todas las estrategias fallaron (solo Spaces)
            logger.error(f"{prefix} ❌ Todas las estrategias de ASL fallaron")
            return {
                "resultado": "Servicio no disponible",
                "confianza": 0.0,
                "alternativas": [],
                "source": "all_failed_spaces",
                "error": "Todos los Spaces ASL están temporalmente no disponibles"
            }
            
        except Exception as e:
            logger.error(f"{prefix} ❌ Error crítico en predicción ASL: {e}")
            return {
                "resultado": "Error del sistema",
                "confianza": 0.0,
                "alternativas": [],
                "source": "system_error",
                "error": str(e)
            }
            
        finally:
            # Limpiar archivo temporal
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

# Instancia global del servicio
gradio_service = GradioCompatibilityService()
