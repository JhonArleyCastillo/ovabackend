import logging
import asyncio
from typing import Optional, Dict, Any
from .resilience_service import ResilienceService

# Importes condicionales para no romper en entornos sin dependencias
try:
    from gradio_client import Client
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False

try:
    from huggingface_hub import InferenceClient
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

try:
    from config import HF_TOKEN, ENVIRONMENT
except Exception:
    from os import getenv
    HF_TOKEN = getenv("HF_TOKEN")
    ENVIRONMENT = getenv("ENVIRONMENT", "development")

logger = logging.getLogger(__name__)

"""
Definición unificada de proveedores de chat.

TIPOS:
 - space  : Hugging Face Space (Gradio UI) => se usa gradio_client.Client
 - model  : Repositorio de modelo puro => se usa InferenceClient (text_generation)"""

CHAT_PROVIDERS = [
    {
        "name": "GPT-OSS-20B Demo Space",
        "resource": "merterbak/gpt-oss-20b-demo",  # Space (Gradio)
        "resource_type": "space",
        "api_name": "/chat",
        "supports_system_prompt": True
    },
    {
        "name": "AMD 120B Chatbot Space",
        "resource": "amd/gpt-oss-120b-chatbot",    # Space (Gradio)
        "resource_type": "space",
        "api_name": "/chat",
        "supports_system_prompt": True
    },
    {
        "name": "DialoGPT Medium (Modelo)",        # Modelo puro (NO Space)
        "resource": "microsoft/DialoGPT-medium",
        "resource_type": "model",
        "supports_system_prompt": False
    }
]

# Ajuste de orden según entorno: en prod podemos priorizar modelo directo (menos latencia UI)
if ENVIRONMENT.lower() == "production":
    CHAT_PROVIDERS = (
        [p for p in CHAT_PROVIDERS if p["resource_type"] == "model"] +
        [p for p in CHAT_PROVIDERS if p["resource_type"] == "space"]
    )

DEFAULT_SYSTEM_PROMPT = "Eres un asistente útil y amigable. Responde de manera clara y concisa en español."

# ================= Utilidades internas ================= #

def _create_space_client(space_slug: str) -> Client:
    """Crea un cliente Gradio para un Space. Usa token si existe (para Spaces privados)."""
    if not GRADIO_AVAILABLE:
        raise RuntimeError("gradio_client no instalado - no se puede usar Spaces")
    kwargs = {}
    if HF_TOKEN:
        kwargs["hf_token"] = HF_TOKEN
    return Client(space_slug, **kwargs)

def _create_model_client(model_id: str) -> InferenceClient:
    """Crea un cliente de inferencia para un modelo puro (sin interfaz Space)."""
    if not HF_AVAILABLE:
        raise RuntimeError("huggingface_hub no instalado - no se puede usar modelos directos")
    return InferenceClient(model=model_id, token=HF_TOKEN) if HF_TOKEN else InferenceClient(model=model_id)

def _invoke_space(provider: Dict[str, Any], user_input: str, system_prompt: Optional[str], max_tokens: int) -> str:
    """
    Invoca un Space de chat de manera robusta probando diferentes firmas comunes.
    Corrige el caso donde algunos Spaces esperan un historial iterable y darían
    'TypeError: bool is not iterable' si reciben False/None.
    """
    client = _create_space_client(provider["resource"])
    api_name = provider.get("api_name", "/chat")
    supports_system = provider.get("supports_system_prompt", False)

    final_system = system_prompt or DEFAULT_SYSTEM_PROMPT if supports_system else None
    history_empty = []  # asegurar iterable por defecto

    # Intento 1: Usar argumentos posicionales para evitar problemas de nombres
    try:
        if supports_system:
            # Para Spaces que soportan system prompt: (message, history, system_prompt, max_tokens, ...)
            result = client.predict(
                user_input,           # mensaje del usuario
                history_empty,        # historial (lista vacía)
                final_system,         # system prompt
                max_tokens,           # tokens máximos
                0.7,                  # temperature
                0.9,                  # top_p
                50,                   # top_k
                1.0,                  # repetition_penalty
                api_name=api_name
            )
        else:
            # Para Spaces sin system prompt: (message, history, max_tokens, ...)
            result = client.predict(
                user_input,           # mensaje del usuario
                history_empty,        # historial (lista vacía)
                max_tokens,           # tokens máximos
                0.7,                  # temperature
                0.9,                  # top_p
                50,                   # top_k
                1.0,                  # repetition_penalty
                api_name=api_name
            )
        return _normalize_result(result, provider)
    except Exception as e1:
        pass

    # Intento 2: Simplificado con solo mensaje e historial
    try:
        result = client.predict(
            user_input,               # mensaje
            history_empty,            # historial como lista vacía
            api_name=api_name
        )
        return _normalize_result(result, provider)
    except Exception as e2:
        pass

    # Intento 3: Solo el mensaje (más básico)
    try:
        result = client.predict(user_input, api_name=api_name)
        return _normalize_result(result, provider)
    except Exception as e3:
        pass

    # Intento 4: Probar sin api_name específico (usar el predeterminado)
    try:
        result = client.predict(user_input, history_empty)
        return _normalize_result(result, provider)
    except Exception as e4:
        raise RuntimeError(f"Todos los intentos de llamada fallaron. Último error: {e4}")

def _invoke_model(provider: Dict[str, Any], user_input: str, system_prompt: Optional[str], max_tokens: int) -> str:
    client = _create_model_client(provider["resource"])
    prompt = (system_prompt or DEFAULT_SYSTEM_PROMPT) + "\nUsuario: " + user_input + "\nAsistente:"
    try:
        # InferenceClient.text_generation devuelve string
        result = client.text_generation(prompt, max_new_tokens=max_tokens, temperature=0.7, top_p=0.9)
        return result.strip()
    except Exception as e:
        raise RuntimeError(f"Fallo modelo {provider['name']}: {e}")

def _normalize_result(result: Any, provider: Dict[str, Any]) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, (list, tuple)) and result:
        return str(result[0])
    return str(result)

def _call_provider(provider: Dict[str, Any], user_input: str, system_prompt: Optional[str], max_tokens: int) -> str:
    kind = provider["resource_type"]
    if kind == "space":
        return _invoke_space(provider, user_input, system_prompt, max_tokens)
    elif kind == "model":
        return _invoke_model(provider, user_input, system_prompt, max_tokens)
    else:
        raise ValueError(f"Tipo de proveedor desconocido: {kind}")

def _get_fallback_response(user_input: str) -> str:
    """Genera una respuesta de respaldo (fallback) inteligente cuando todos los proveedores fallan."""
    user_lower = user_input.lower()
    
    # Saludos y presentaciones
    if any(greeting in user_lower for greeting in ["hola", "hello", "hi", "buenos días", "buenas tardes", "buenas noches"]):
        return "¡Hola! 👋 Soy tu asistente virtual OVA. Aunque el servicio de IA avanzada no está disponible en este momento, puedo ayudarte con información básica y responder preguntas simples. ¿En qué puedo asistirte?"
    
    # Preguntas sobre programación
    elif any(term in user_lower for term in ["python", "javascript", "programación", "código", "html", "css"]):
        return "¡Me encanta hablar de programación! 💻 Aunque no tengo acceso al modelo de IA completo ahora, puedo ayudarte con conceptos básicos. Python es un lenguaje de programación versátil, JavaScript es esencial para web, y HTML/CSS son la base del diseño web. ¿Hay algo específico que te gustaría saber?"
    
    # Preguntas sobre inteligencia artificial
    elif any(term in user_lower for term in ["inteligencia artificial", "ia", "ai", "machine learning", "aprendizaje automático"]):
        return "🤖 La Inteligencia Artificial es fascinante! Es la tecnología que permite a las máquinas realizar tareas que normalmente requieren inteligencia humana, como reconocer patrones, tomar decisiones y procesar lenguaje natural. Incluye campos como machine learning, deep learning y redes neuronales. ¿Te interesa algún aspecto específico?"
    
    # Preguntas generales de conocimiento
    elif any(question in user_lower for question in ["qué es", "que es", "cómo", "como", "cuál", "cual", "por qué", "porque", "why", "what", "how"]):
        if "fotosíntesis" in user_lower:
            return "🌱 La fotosíntesis es el proceso por el cual las plantas convierten la luz solar, agua y dióxido de carbono en glucosa y oxígeno. Es fundamental para la vida en la Tierra porque produce el oxígeno que respiramos y es la base de la cadena alimentaria."
        elif "gravity" in user_lower or "gravedad" in user_lower:
            return "🌍 La gravedad es la fuerza de atracción entre objetos con masa. En la Tierra, nos mantiene con los pies en el suelo y hace que los objetos caigan hacia el centro del planeta."
        else:
            return "Es una pregunta interesante! 🤔 Aunque no tengo acceso al modelo de IA completo en este momento, puedo intentar ayudarte con información básica. ¿Podrías reformular tu pregunta de manera más específica?"
    
    # Chistes y entretenimiento
    elif any(term in user_lower for term in ["chiste", "joke", "divertido", "gracioso"]):
        chistes = [
            "¿Por qué los programadores prefieren el modo oscuro? Porque la luz atrae bugs! 🐛💻",
            "¿Cómo llamas a un robot que toma el camino más largo? R2-Detrús! 🤖",
            "¿Por qué los desarrolladores odian la naturaleza? Porque tiene demasiados bugs! 🌿🐛"
        ]
        import random
        return random.choice(chistes)
    
    # Agradecimientos
    elif any(thanks in user_lower for thanks in ["gracias", "thanks", "thank you", "muchas gracias"]):
        return "¡De nada! 😊 Aunque el servicio completo de IA no esté disponible, me alegra poder ayudarte con lo que puedo. Si necesitas algo más específico, ¡no dudes en preguntar!"
    
    # Despedidas
    elif any(bye in user_lower for bye in ["adiós", "adios", "bye", "hasta luego", "nos vemos"]):
        return "¡Hasta luego! 👋 Fue un placer ayudarte. Vuelve cuando necesites asistencia. ¡Que tengas un excelente día!"
    
    # Consultas sobre el estado del servicio
    elif any(term in user_lower for term in ["funciona", "disponible", "servicio", "error"]):
        return "🔧 El servicio de IA avanzada está temporalmente no disponible debido a limitaciones de cuota en los servidores externos. Sin embargo, puedo ayudarte con respuestas básicas y información general. ¿Hay algo específico en lo que pueda asistirte mientras tanto?"
    
    # Respuesta general
    else:
        return f"He recibido tu mensaje: '{user_input}' 📝\n\nAunque el modelo de IA completo no está disponible ahora, estoy aquí para ayudarte con información básica. Puedo responder preguntas sobre programación, ciencia, tecnología, o simplemente conversar contigo. ¿En qué te gustaría que te ayude?"

@ResilienceService.resilient_hf_call(
    timeout_seconds=30.0,  # Reducido para ser más responsivo
    retry_attempts=2,      # Menos intentos para endpoints lentos
    fallback_response="Lo siento, el servicio no está disponible en este momento. Por favor, inténtalo más tarde."
)
async def get_llm_response_async(user_input: str, system_prompt: str = None, max_tokens: int = 1024) -> str:
    """Obtiene una respuesta consultando múltiples proveedores con fallback automático."""
    try:
        # Ejecutar la llamada con fallbacks en un thread separado para mantener async
        response = await asyncio.get_event_loop().run_in_executor(
            None, _call_with_fallbacks, user_input, system_prompt, max_tokens
        )
        logger.info(f"Respuesta generada para: '{user_input[:30]}...'")
        return response
    except Exception as e:
        logger.error(f"Error al obtener respuesta: {e}")
        raise

def _call_with_fallbacks(user_input: str, system_prompt: str = None, max_tokens: int = 1024) -> str:
    """Prueba cada proveedor en orden y aplica fallback si falla, hasta agotar opciones."""
    for i, provider in enumerate(CHAT_PROVIDERS):
        try:
            logger.info(f"🔄 Proveedor {i+1}/{len(CHAT_PROVIDERS)}: {provider['name']} ({provider['resource_type']})")
            response = _call_provider(provider, user_input, system_prompt, max_tokens)
            logger.info(f"✅ Éxito con {provider['name']}")
            return response
        except Exception as e:
            error_msg = str(e)
            # Detectar errores específicos de bool iteration
            if "'bool' object is not iterable" in error_msg:
                logger.warning(f"❌ {provider['name']}: Error de tipo bool no iterable - probablemente parámetros incorrectos para la API Gradio")
            elif "argument of type 'bool' is not iterable" in error_msg:
                logger.warning(f"❌ {provider['name']}: Error de argumento bool - verificando firma de API")
            else:
                logger.warning(f"❌ Falló {provider['name']}: {e}")
            
            if i == len(CHAT_PROVIDERS) - 1:
                logger.info("⚙️ Usando fallback local static")
                return _get_fallback_response(user_input)
            continue
    return _get_fallback_response(user_input)

def get_llm_response(user_input: str, system_prompt: str = None, max_tokens: int = 1024) -> str:
    """Obtiene una respuesta consultando proveedores con fallback (versión síncrona)."""
    try:
        return _call_with_fallbacks(user_input, system_prompt, max_tokens)
    except Exception as e:
        logger.error(f"Error al obtener respuesta: {e}")
        return _get_fallback_response(user_input)

# APIs externas migradas a gradio_client - código legacy limpiado 